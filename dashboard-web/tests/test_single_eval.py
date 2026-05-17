"""Tests for services.single_eval — writes single-row batch input."""

from __future__ import annotations

import csv

from services import single_eval


def test_request_construction():
    req = single_eval.SingleEvalRequest(
        num=42,
        url="https://example.com/role",
        company="ACME",
        role="Director of AI",
    )
    assert req.num == 42
    assert req.url == "https://example.com/role"
    assert req.company == "ACME"


def test_is_busy_returns_false_when_no_lock(temp_root):
    assert single_eval.is_busy() is False


def test_is_busy_returns_false_for_dead_pid(temp_root):
    # Write a pid that almost certainly doesn't exist
    lock = temp_root / "batch" / "batch-runner.pid"
    lock.parent.mkdir(parents=True, exist_ok=True)
    lock.write_text("999999999\n", encoding="utf-8")
    assert single_eval.is_busy() is False


def test_input_tsv_written_correctly(temp_root, monkeypatch):
    """Even without actually running bash, the input file should be written."""
    import services.batch as batch_svc
    monkeypatch.setattr(batch_svc, "find_bash", lambda: None)
    req = single_eval.SingleEvalRequest(num=7, url="https://example.com/x", company="X", role="Y")
    try:
        single_eval.run_single(req)
        assert False, "should have raised"
    except RuntimeError as e:
        assert "bash" in str(e).lower()


def test_input_tsv_written_when_bash_and_claude_present(temp_root, monkeypatch):
    """Mock both bash and claude as present, then mock subprocess.Popen to confirm
    the input TSV is written before spawn."""
    import services.batch as batch_svc
    import services.single_eval as se
    monkeypatch.setattr(batch_svc, "find_bash", lambda: "/usr/bin/bash")
    monkeypatch.setattr(batch_svc, "claude_cli_available", lambda: True)

    # Replace Popen with a stub that just records args
    captured = {}
    class FakeProc:
        pid = 12345
    def fake_popen(args, **kw):
        captured["args"] = args
        captured["cwd"] = kw.get("cwd")
        return FakeProc()
    monkeypatch.setattr(se.subprocess, "Popen", fake_popen)

    # Need an actual batch-runner.sh placeholder
    (temp_root / "batch" / "batch-runner.sh").write_text("#!/bin/bash\necho ok\n", encoding="utf-8")

    req = se.SingleEvalRequest(num=7, url="https://example.com/x", company="ACME", role="Director")
    proc = se.run_single(req)
    assert proc.pid == 12345

    tsv = temp_root / "batch" / "batch-input.tsv"
    assert tsv.exists()
    with tsv.open() as f:
        rows = list(csv.reader(f, delimiter="\t"))
    assert rows[0] == ["id", "url", "source", "notes"]
    assert rows[1][0] == "7"
    assert rows[1][1] == "https://example.com/x"
    assert rows[1][2] == "dashboard-single"
