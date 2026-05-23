"""Single-role evaluation — wraps batch-runner.sh for one row.

We use the same batch contract (batch-input.tsv → batch-runner.sh) but
populate it with exactly one offer. This produces score + report + PDF +
cover letter for the single role, indistinguishable from the bulk path.
"""

from __future__ import annotations

import csv
import time
import subprocess
from dataclasses import dataclass
from pathlib import Path

from . import project_root
from . import batch as batch_svc


@dataclass
class SingleEvalRequest:
    num: int
    url: str
    company: str
    role: str
    template: str = ""  # CV template slug; empty = runner default (classic)


def run_single(req: SingleEvalRequest) -> subprocess.Popen:
    """Spawn batch-runner.sh with a 1-row input. Returns Popen; caller polls state.
    Forces re-evaluation by wiping any existing state row for this id."""
    bash_exe = batch_svc.find_bash()
    if not bash_exe:
        raise RuntimeError(
            "bash not found. Install Git for Windows (https://git-scm.com/download/win) "
            "or WSL — needed to run batch-runner.sh."
        )
    if not batch_svc.claude_cli_available():
        raise RuntimeError("claude CLI not found — install Claude Code first.")

    input_path = project_root() / "batch" / "batch-input.tsv"
    input_path.parent.mkdir(parents=True, exist_ok=True)
    with input_path.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, delimiter="\t", lineterminator="\n")
        w.writerow(["id", "url", "source", "notes"])
        w.writerow([req.num, req.url, "dashboard-single", f"{req.company}: {req.role}"[:120]])

    # Force fresh evaluation: drop any prior state row for this id so the
    # runner doesn't skip it as already completed.
    state_path = project_root() / "batch" / "batch-state.tsv"
    if state_path.exists():
        try:
            lines = state_path.read_text(encoding="utf-8").splitlines()
            if lines:
                header = lines[0]
                kept = [ln for ln in lines[1:] if not ln.strip().startswith(f"{req.num}\t")]
                state_path.write_text("\n".join([header] + kept) + "\n", encoding="utf-8")
        except Exception:
            pass

    log_dir = project_root() / "batch" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / f"single-{req.num}-{int(time.time())}.log"
    log_fh = log_path.open("w", encoding="utf-8")

    runner = project_root() / "batch" / "batch-runner.sh"
    cmd = [bash_exe, str(runner), "--parallel", "1"]
    if req.template:
        cmd.extend(["--template", req.template])
    proc = subprocess.Popen(
        cmd,
        cwd=str(project_root()),
        stdin=subprocess.DEVNULL,  # avoid claude -p "no stdin data" warning
        stdout=log_fh,
        stderr=subprocess.STDOUT,
    )
    return proc


def is_busy() -> bool:
    """True if batch-runner is currently holding the lock."""
    lock = project_root() / "batch" / "batch-runner.pid"
    if not lock.exists():
        return False
    try:
        pid = int(lock.read_text(encoding="utf-8").strip())
    except Exception:
        return False
    # Cross-platform check
    try:
        if pid <= 0:
            return False
        # On Windows, signal 0 is not supported; use a tasklist check instead
        import os, signal
        try:
            os.kill(pid, 0)
            return True
        except OSError:
            return False
    except Exception:
        return False
