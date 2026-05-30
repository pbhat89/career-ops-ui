"""Tests for services.batch — input enqueue + state summary."""

from __future__ import annotations

import csv
import subprocess
import sys

from services import batch, tracker


def test_evaluable_pending_filters_rows_without_url(temp_root):
    df = tracker.load_applications()
    pending = batch.evaluable_pending(df)
    # JPMorgan (num=3) has a URL in notes → evaluable
    assert 3 in pending["num"].tolist()
    # Nomura (num=4) has no URL → not evaluable
    assert 4 not in pending["num"].tolist()
    # HSBC is Evaluated, not Pending → excluded
    assert 1 not in pending["num"].tolist()


def test_write_input_tsv_creates_valid_file(temp_root):
    rows = [
        batch.BatchRow(id=3, url="https://example.com/a", source="test", notes="alpha"),
        batch.BatchRow(id=4, url="https://example.com/b", source="test", notes="beta"),
    ]
    path = batch.write_input_tsv(rows)
    assert path.exists()
    with path.open("r", encoding="utf-8") as f:
        reader = csv.reader(f, delimiter="\t")
        header = next(reader)
        body = list(reader)
    assert header == ["id", "url", "source", "notes"]
    assert body[0] == ["3", "https://example.com/a", "test", "alpha"]
    assert body[1] == ["4", "https://example.com/b", "test", "beta"]


def test_rows_from_dataframe_handles_pending_subset(temp_root):
    df = tracker.load_applications()
    pending = batch.evaluable_pending(df)
    rows = batch.rows_from_dataframe(pending)
    assert all(isinstance(r, batch.BatchRow) for r in rows)
    assert all(r.url.startswith("http") for r in rows)


def test_read_state_empty_when_no_file(temp_root):
    state = batch.read_state()
    assert state.empty
    summary = batch.state_summary()
    assert summary["total"] == 0


def test_read_state_parses_existing_file(temp_root):
    state_path = temp_root / "batch" / "batch-state.tsv"
    state_path.write_text(
        "id\turl\tstatus\tstarted_at\tcompleted_at\treport_num\tscore\terror\tretries\n"
        "1\thttps://x\tcompleted\t2026-05-16\t2026-05-16\t003\t4.3\t-\t0\n"
        "2\thttps://y\tfailed\t2026-05-16\t2026-05-16\t-\t-\ttimeout\t2\n"
        "3\thttps://z\tin_progress\t2026-05-16\t-\t-\t-\t-\t0\n",
        encoding="utf-8",
    )
    s = batch.state_summary()
    assert s["total"] == 3
    assert s["completed"] == 1
    assert s["failed"] == 1
    assert s["in_progress"] == 1


def test_runner_alive_is_accurate_and_non_destructive(temp_root):
    """runner_alive() must report liveness WITHOUT signalling the process.

    Regression guard: on Windows os.kill(pid, 0) is not a no-op probe — it can
    terminate the target. The live-progress autorefresh calls runner_alive()
    every couple of seconds, so a destructive check would kill the very batch
    runner it is polling. Must be a pure query on every platform."""
    pid_file = temp_root / "batch" / "batch-runner.pid"
    pid_file.parent.mkdir(parents=True, exist_ok=True)

    proc = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)"])
    try:
        pid_file.write_text(str(proc.pid), encoding="utf-8")
        # Reports alive...
        assert batch.runner_alive() is True
        # ...and the probe did NOT kill it (poll() stays None while running).
        assert proc.poll() is None
        # A second probe is still safe.
        assert batch.runner_alive() is True
        assert proc.poll() is None
    finally:
        proc.terminate()
        proc.wait(timeout=10)

    # Once the process is gone, liveness flips to False.
    assert batch.runner_alive() is False

    # Bogus / unparseable pid → not alive, never raises.
    pid_file.write_text("99999999", encoding="utf-8")
    assert batch.runner_alive() is False
    pid_file.write_text("not-a-pid", encoding="utf-8")
    assert batch.runner_alive() is False


def test_bash_and_claude_availability_smoke(temp_root):
    # Just verify the functions return booleans without exploding.
    assert isinstance(batch.bash_available(), bool)
    assert isinstance(batch.claude_cli_available(), bool)
