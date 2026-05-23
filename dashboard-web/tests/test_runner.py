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
