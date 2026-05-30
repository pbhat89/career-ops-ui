"""Tests for services.runner — subprocess wrapper basics + new helpers."""

from __future__ import annotations

import shutil

import pytest

from services import runner


def test_node_resolves_when_available():
    if shutil.which("node") is None and shutil.which("node.exe") is None:
        pytest.skip("node not on PATH")
    assert runner._node()


def test_run_script_missing_returns_failure(temp_root):
    result = runner.run_script("does-not-exist.mjs")
    assert result.ok is False
    assert result.returncode == 127
    assert "not found" in result.stderr.lower()


def test_run_script_executes_real_node(temp_root, tmp_path):
    if shutil.which("node") is None and shutil.which("node.exe") is None:
        pytest.skip("node not on PATH")
    script = temp_root / "hello.mjs"
    script.write_text('console.log(JSON.stringify({hello: "world"}));\n', encoding="utf-8")
    result = runner.run_script("hello.mjs")
    assert result.ok, result.stderr
    assert '"world"' in result.stdout
    assert result.json() == {"hello": "world"}


def test_run_result_json_handles_preamble_noise():
    """If stdout has warning text BEFORE the JSON line, .json() should still
    pick up the trailing JSON object (the contract scan.mjs --json gives us)."""
    r = runner.RunResult(
        ok=True,
        stdout='Warning: experimental feature\n{"new_offers": 3, "ok": true}\n',
        stderr="",
        returncode=0,
    )
    payload = r.json()
    assert payload is not None
    assert payload["new_offers"] == 3
    assert payload["ok"] is True


def test_run_result_json_returns_none_for_garbage():
    r = runner.RunResult(ok=True, stdout="this is not json at all", stderr="", returncode=0)
    assert r.json() is None


def test_scan_summary_returns_dict_on_node_failure(temp_root, monkeypatch):
    """When node is missing or scan.mjs fails, scan_summary still returns a
    structured dict instead of None — so dashboard code can show errors safely."""
    # Force the underlying script to fail
    def boom(*args, **kwargs):
        return runner.RunResult(ok=False, stdout="", stderr="simulated failure", returncode=1)

    monkeypatch.setattr(runner, "run_script", boom)
    payload = runner.scan_summary(dry_run=True, company="Anthropic")
    assert isinstance(payload, dict)
    assert payload["ok"] is False
    assert payload["new_offers"] == 0
    assert "simulated failure" in payload["errors"][0]["error"]


def test_scan_summary_parses_real_json(temp_root, monkeypatch):
    """A well-formed JSON payload from scan.mjs should be passed through."""
    fake_json = (
        '{"ok": true, "new_offers": 2, "companies_scanned": 5, '
        '"filtered": 3, "duplicates": 1, '
        '"offers": [{"company": "Foo", "title": "Head of AI", "url": "https://x", "location": "SG"}], '
        '"errors": []}'
    )

    def fake_run(*args, **kwargs):
        return runner.RunResult(ok=True, stdout=fake_json, stderr="", returncode=0)

    monkeypatch.setattr(runner, "run_script", fake_run)
    payload = runner.scan_summary(dry_run=False, company=None)
    assert payload["ok"] is True
    assert payload["new_offers"] == 2
    assert payload["companies_scanned"] == 5
    assert len(payload["offers"]) == 1
    assert payload["offers"][0]["company"] == "Foo"


def test_scan_args_builds_title_and_company_flags():
    args = runner._scan_args(dry_run=True, company="Swiss Re",
                             titles=["Chief Data", "Head of Risk"], json_out=True)
    assert "--dry-run" in args
    assert args[args.index("--company") + 1] == "Swiss Re"
    # Each title becomes its own --title <value> pair.
    title_idxs = [i for i, a in enumerate(args) if a == "--title"]
    assert len(title_idxs) == 2
    assert args[title_idxs[0] + 1] == "Chief Data"
    assert args[title_idxs[1] + 1] == "Head of Risk"
    assert "--json" in args


def test_scan_args_drops_blank_titles():
    args = runner._scan_args(dry_run=False, company=None,
                             titles=["", "  ", "VP Analytics"], json_out=False)
    assert args.count("--title") == 1
    assert args[args.index("--title") + 1] == "VP Analytics"
    assert "--json" not in args
    assert "--company" not in args


def test_scan_summary_passes_titles_through(temp_root, monkeypatch):
    captured = {}

    def fake_run(script, *args, **kwargs):
        captured["args"] = args
        return runner.RunResult(ok=True, stdout='{"ok": true, "new_offers": 0, "offers": []}',
                                stderr="", returncode=0)

    monkeypatch.setattr(runner, "run_script", fake_run)
    runner.scan_summary(dry_run=False, company=None, titles=["Head of AI"])
    assert "--title" in captured["args"]
    assert "Head of AI" in captured["args"]


# ── WebSearch scan (claude -p path) ───────────────────────────────────

def test_build_websearch_prompt_company():
    p = runner.build_websearch_prompt([], company="Munich Re", titles=None)
    assert "Munich Re" in p
    assert "JSON array" in p
    assert "company, title, url, location" in p


def test_build_websearch_prompt_titles():
    p = runner.build_websearch_prompt([], company=None, titles=["Chief Data Officer", "Head of AI"])
    assert '"Chief Data Officer"' in p and '"Head of AI"' in p


def test_build_websearch_prompt_queries_caps_at_max():
    qs = [f"query-{i}" for i in range(20)]
    p = runner.build_websearch_prompt(qs, max_queries=3)
    assert "query-0" in p and "query-2" in p
    assert "query-3" not in p


def test_parse_offers_plain_array():
    txt = '[{"company":"Foo","title":"Head of AI","url":"https://x","location":"SG"}]'
    offers = runner._parse_offers_from_text(txt)
    assert len(offers) == 1
    assert offers[0]["source"] == "websearch"
    assert offers[0]["company"] == "Foo"


def test_parse_offers_fenced_and_prose():
    txt = 'Here are the jobs I found:\n```json\n[{"company":"Bar","title":"CDO","url":"https://y","location":""}]\n```\nDone.'
    offers = runner._parse_offers_from_text(txt)
    assert len(offers) == 1 and offers[0]["company"] == "Bar"


def test_parse_offers_requires_company_title_url():
    assert runner._parse_offers_from_text("no json here") == []
    txt = (
        '[{"company":"NoUrl","title":"X"},'          # missing url -> drop
        '{"title":"Y","url":"https://z"},'           # missing company -> drop
        '{"company":"Real","url":"https://w"},'      # missing title -> drop
        '{"company":"Good","title":"Head of AI","url":"https://ok","location":"SG"}]'
    )
    offers = runner._parse_offers_from_text(txt)
    assert len(offers) == 1
    assert offers[0]["company"] == "Good" and offers[0]["url"] == "https://ok"


def test_websearch_scan_no_claude(temp_root, monkeypatch):
    import services.batch as _batch
    monkeypatch.setattr(_batch, "find_claude", lambda: None)
    res = runner.websearch_scan(company="Munich Re")
    assert res["ok"] is False
    assert res["hint"] == "no-claude"
    assert res["new_offers"] == 0


def test_websearch_scan_parses_offers(temp_root, monkeypatch):
    import services.batch as _batch
    monkeypatch.setattr(_batch, "find_claude", lambda: "claude")

    class _Proc:
        returncode = 0
        stdout = '{"result": "[{\\"company\\":\\"Foo\\",\\"title\\":\\"Head of AI\\",\\"url\\":\\"https://x\\",\\"location\\":\\"SG\\"}]", "is_error": false}'
        stderr = ""

    monkeypatch.setattr(runner.subprocess, "run", lambda *a, **k: _Proc())
    res = runner.websearch_scan(company="Foo")
    assert res["ok"] is True
    assert res["new_offers"] == 1
    assert res["offers"][0]["company"] == "Foo"
    assert res["offers"][0]["source"] == "websearch"


def test_websearch_scan_handles_claude_failure(temp_root, monkeypatch):
    import services.batch as _batch
    monkeypatch.setattr(_batch, "find_claude", lambda: "claude")

    class _Proc:
        returncode = 1
        stdout = ""
        stderr = "boom"

    monkeypatch.setattr(runner.subprocess, "run", lambda *a, **k: _Proc())
    res = runner.websearch_scan(titles=["CDO"])
    assert res["ok"] is False
    assert "boom" in res["errors"][0]["error"]
