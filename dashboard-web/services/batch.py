"""Batch evaluation orchestrator — wraps batch/batch-runner.sh.

The runner shells out one `claude -p` worker per pending URL and produces
a full evaluation (score + report + PDF + cover letter). We surface it as
a single "Evaluate all pending" action in the UI.
"""

from __future__ import annotations

import csv
import shutil
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import pandas as pd

from . import project_root


BATCH_DIR = "batch"
INPUT_TSV = "batch/batch-input.tsv"
STATE_TSV = "batch/batch-state.tsv"
RUNNER = "batch/batch-runner.sh"


@dataclass
class BatchRow:
    id: int
    url: str
    source: str = ""
    notes: str = ""


_BASH_FALLBACKS = (
    r"C:\Program Files\Git\bin\bash.exe",
    r"C:\Program Files\Git\usr\bin\bash.exe",
    r"C:\Program Files (x86)\Git\bin\bash.exe",
    r"C:\Windows\System32\bash.exe",  # WSL
)

_CLAUDE_FALLBACKS = (
    r"C:\Users\{user}\AppData\Roaming\npm\claude.cmd",
    r"C:\Users\{user}\AppData\Roaming\npm\claude",
)


def find_bash() -> str | None:
    """Resolve a bash executable. Tries PATH first, then common Git/WSL locations."""
    p = shutil.which("bash") or shutil.which("bash.exe")
    if p:
        return p
    from pathlib import Path
    for candidate in _BASH_FALLBACKS:
        if Path(candidate).exists():
            return candidate
    return None


def find_claude() -> str | None:
    """Resolve the claude CLI executable. PATH first, then npm global install dir."""
    import os
    from pathlib import Path
    p = shutil.which("claude") or shutil.which("claude.cmd") or shutil.which("claude.exe")
    if p:
        return p
    user = os.environ.get("USERNAME") or os.environ.get("USER") or ""
    if user:
        for tmpl in _CLAUDE_FALLBACKS:
            candidate = tmpl.replace("{user}", user)
            if Path(candidate).exists():
                return candidate
    return None


def claude_cli_available() -> bool:
    return find_claude() is not None


def bash_available() -> bool:
    return find_bash() is not None


def evaluable_pending(df: pd.DataFrame) -> pd.DataFrame:
    """Pending rows that have a usable JD URL (the batch runner needs one)."""
    if df.empty:
        return df.iloc[0:0]
    return df[(df["status"] == "Pending") & df["job_url"].notna() & (df["job_url"] != "")]


def write_input_tsv(rows: Iterable[BatchRow]) -> Path:
    path = project_root() / INPUT_TSV
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, delimiter="\t", lineterminator="\n")
        w.writerow(["id", "url", "source", "notes"])
        for r in rows:
            w.writerow([r.id, r.url, r.source, r.notes])
    return path


def rows_from_dataframe(df: pd.DataFrame) -> list[BatchRow]:
    out: list[BatchRow] = []
    for _, r in df.iterrows():
        out.append(BatchRow(
            id=int(r["num"]),
            url=str(r["job_url"]),
            source="dashboard",
            notes=str(r.get("company", ""))[:80],
        ))
    return out


def start_batch(parallel: int = 1, dry_run: bool = False) -> subprocess.Popen:
    """Spawn the batch-runner in the background. Returns the Popen handle
    so the UI can poll state from batch-state.tsv."""
    bash_exe = find_bash()
    if not bash_exe:
        raise RuntimeError(
            "bash not found. Install Git for Windows (https://git-scm.com/download/win) "
            "or WSL — needed to run batch-runner.sh."
        )
    if not claude_cli_available():
        raise RuntimeError("claude CLI not found — install Claude Code first.")

    runner_path = project_root() / RUNNER
    if not runner_path.exists():
        raise FileNotFoundError(f"Missing {RUNNER}")

    args = [bash_exe, str(runner_path), "--parallel", str(parallel)]
    if dry_run:
        args.append("--dry-run")

    log_path = project_root() / "batch" / "logs" / f"runner-{int(time.time())}.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_fh = log_path.open("w", encoding="utf-8")
    proc = subprocess.Popen(
        args,
        cwd=str(project_root()),
        stdin=subprocess.DEVNULL,  # avoid claude -p "no stdin data" warning
        stdout=log_fh,
        stderr=subprocess.STDOUT,
    )
    return proc


def runner_alive() -> bool:
    """Public alias — True if a batch-runner process is currently alive.

    The UI uses this to keep the live-progress autorefresh running during the
    launch handshake (the bash + claude CLI take a few seconds to write the
    first 'processing' row, before which the state snapshot looks idle)."""
    return _runner_alive()


def _pid_alive(pid: int) -> bool:
    """Non-destructive 'is this pid running?' check, cross-platform.

    On POSIX, os.kill(pid, 0) is the canonical no-op liveness probe. On Windows
    it is NOT — Python maps signal 0 to a console-control / TerminateProcess path
    that can actually kill the target. So on Windows we query the process via the
    Win32 API instead (OpenProcess + GetExitCodeProcess) and never signal it."""
    if pid <= 0:
        return False
    import os
    if os.name == "nt":
        import ctypes
        from ctypes import wintypes
        PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
        STILL_ACTIVE = 259
        kernel32 = ctypes.windll.kernel32
        handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
        if not handle:
            return False  # no such process (or no access — treat as gone)
        try:
            code = wintypes.DWORD()
            if not kernel32.GetExitCodeProcess(handle, ctypes.byref(code)):
                return False
            return code.value == STILL_ACTIVE
        finally:
            kernel32.CloseHandle(handle)
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def _runner_alive() -> bool:
    """True if the pid in batch-runner.pid is a live process."""
    pid_file = project_root() / "batch" / "batch-runner.pid"
    if not pid_file.exists():
        return False
    try:
        pid = int(pid_file.read_text(encoding="utf-8").strip())
        return _pid_alive(pid)
    except Exception:
        return False


def _reconcile_state(df: pd.DataFrame) -> pd.DataFrame:
    """If batch-runner is no longer alive AND a row sits at 'processing',
    look at disk evidence (tracker-additions/{id}.tsv) to mark it completed.
    Persists the corrected state back to disk so subsequent reads stay clean.
    """
    if df.empty:
        return df
    if _runner_alive():
        return df  # runner still working, don't interfere

    root = project_root()
    tracker_dir = root / "batch" / "tracker-additions"
    state_path = root / STATE_TSV
    changed = False

    for idx, row in df.iterrows():
        status = str(row.get("status", "")).lower()
        if status not in ("processing", "in_progress", "pending"):
            continue
        rid = str(row.get("id", "")).strip()
        if not rid:
            continue
        # If a tracker-addition exists for this id, the worker finished
        tsv = tracker_dir / f"{rid}.tsv"
        merged_tsv = tracker_dir / "merged" / f"{rid}.tsv"
        if tsv.exists() or merged_tsv.exists():
            df.at[idx, "status"] = "completed"
            if not str(df.at[idx, "completed_at"]).strip() or df.at[idx, "completed_at"] in ("-", "nan"):
                import datetime as _dt
                df.at[idx, "completed_at"] = _dt.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
            changed = True

    if changed:
        try:
            df.to_csv(state_path, sep="\t", index=False)
        except Exception:
            pass
        # Also remove the stale pid lock
        pid_lock = root / "batch" / "batch-runner.pid"
        if pid_lock.exists():
            try:
                pid_lock.unlink()
            except Exception:
                pass

    return df


def read_state() -> pd.DataFrame:
    """Snapshot of batch-state.tsv — empty df if not yet written.
    Auto-reconciles 'processing' rows when the runner is no longer alive."""
    path = project_root() / STATE_TSV
    if not path.exists():
        return pd.DataFrame(columns=["id", "url", "status", "started_at", "completed_at", "report_num", "score", "error", "retries"])
    try:
        df = pd.read_csv(path, sep="\t", dtype=str)
    except Exception:
        return pd.DataFrame()
    return _reconcile_state(df)


def state_summary() -> dict:
    df = read_state()
    if df.empty:
        return {"total": 0, "completed": 0, "failed": 0, "in_progress": 0, "pending": 0, "active": False}
    counts = df["status"].value_counts().to_dict()
    in_progress = int(counts.get("in_progress", 0) + counts.get("processing", 0))
    pending = int(counts.get("pending", 0))
    completed = int(counts.get("completed", 0))
    failed = int(counts.get("failed", 0))
    return {
        "total": len(df),
        "completed": completed,
        "failed": failed,
        "in_progress": in_progress,
        "pending": pending,
        "active": (in_progress + pending) > 0,
    }


def auto_merge_if_pending() -> int:
    """If there are tracker-addition TSVs that haven't been merged into
    applications.md yet, run merge-tracker.mjs. Returns number of files
    that look pending. Safe to call every render — merge-tracker.mjs is idempotent."""
    tracker_dir = project_root() / "batch" / "tracker-additions"
    if not tracker_dir.exists():
        # Even if there's nothing fresh to merge, an earlier merge may have
        # left orphan Pending rows behind (URL re-resolved to a different
        # company/role and merge-tracker created a new row instead of
        # updating the original). Sweep those up.
        auto_cleanup_orphan_pending()
        return 0
    pending = [p for p in tracker_dir.glob("*.tsv") if p.is_file()]
    if not pending:
        auto_cleanup_orphan_pending()
        return 0
    # Run merge silently in background — don't block UI
    from . import runner as runner_svc
    runner_svc.merge_tracker()
    # merge-tracker.mjs creates NEW rows when the resolved company/role
    # differs from the original Pending row's. Clean up the orphans it
    # leaves behind — idempotent, won't re-fire once a row is Discarded.
    auto_cleanup_orphan_pending()
    return len(pending)


def auto_cleanup_orphan_pending() -> int:
    """Sweep orphan Pending rows whose batch evaluation landed under a
    different row number.

    Scenario: batch ID N processes a URL; the worker resolves the URL to
    company "X" / role "Y" which differs from the original Pending row's
    placeholder ("TBD (CDO direct report)" → "GXS Bank", etc.). When
    merge-tracker.mjs ingests the TSV, it creates a NEW row for "X / Y"
    instead of updating row N, so row N stays Pending forever even though
    its URL has been fully evaluated under a different row.

    Logic per completed batch entry (id, url):
      1. Find apps.md row with num == id.
      2. Skip if it's not Pending or already has a report_path (correctly merged).
      3. Look for the destination row: any OTHER apps.md row whose report URL
         matches the batch URL. If found, mark row N as Discarded with a
         breadcrumb pointing at the destination row + report + score.
      4. Otherwise, if the batch state shows a null/missing score (worker
         produced an unusable report — e.g. report 007 JPMorgan FAILED), still
         retire the orphan with a "no usable score" note so it stops cluttering
         the Pending view.

    Returns the number of rows changed. Idempotent — once a row is Discarded
    it no longer matches the Pending filter.

    Note: the breadcrumb appended to notes is bounded at 100 chars so that
    repeated long Pending notes don't bloat the table.
    """
    from . import tracker

    state_df = read_state()
    if state_df.empty:
        return 0
    completed = state_df[state_df["status"].astype(str).str.lower() == "completed"]
    if completed.empty:
        return 0

    apps_df = tracker.load_applications()
    if apps_df.empty:
        return 0

    # Build a URL → (num, report_num, score, score_raw) index over rows that
    # actually have a report_path (i.e. the merge landed somewhere real).
    url_to_dest: dict[str, dict] = {}
    for _, r in apps_df.iterrows():
        dest_url = r.get("job_url")
        if not dest_url or not str(r.get("report_path", "")).strip():
            continue
        url_to_dest[str(dest_url).strip()] = {
            "num": int(r["num"]),
            "report_num": str(r.get("report_num", "")),
            "score_raw": str(r.get("score_raw", "")),
        }

    changed = 0
    for _, b in completed.iterrows():
        try:
            bid = int(str(b["id"]).strip())
        except (ValueError, TypeError):
            continue
        burl = str(b.get("url", "")).strip()
        if not burl:
            continue

        # Find the apps.md row that shares the batch id (orphan candidate).
        match = apps_df[apps_df["num"] == bid]
        if match.empty:
            continue
        row = match.iloc[0]
        if str(row.get("status", "")).strip() != "Pending":
            continue
        if str(row.get("report_path", "")).strip():
            continue  # already merged into this row — not an orphan

        # Try to find the destination row by URL match.
        dest = url_to_dest.get(burl)
        if dest is None:
            # Also try matching against the destination row's job_url if it
            # differs only by a trailing slash — common between batch state
            # and report header.
            for candidate_url, candidate_dest in url_to_dest.items():
                if candidate_url.rstrip("/") == burl.rstrip("/") and candidate_dest["num"] != bid:
                    dest = candidate_dest
                    break

        if dest is not None and dest["num"] != bid:
            note = (
                f"Re-evaluated as row {dest['num']} / report {dest['report_num']} "
                f"({dest['score_raw']})."
            )
            if len(note) > 100:
                note = note[:97] + "..."
            tracker.update_status(bid, "Discarded", note_append=note)
            changed += 1
            continue

        # No destination row — but if the batch state has no usable score and
        # a report number, retire the orphan with a pointer to the failed report.
        score_raw = str(b.get("score", "")).strip()
        report_num = str(b.get("report_num", "")).strip()
        score_is_null = score_raw in ("", "-", "nan", "N/A", "None")
        if score_is_null and report_num and report_num not in ("-", "nan"):
            note = f"Batch evaluation produced no usable score; see report {report_num}."
            if len(note) > 100:
                note = note[:97] + "..."
            tracker.update_status(bid, "Discarded", note_append=note)
            changed += 1

    return changed


def currently_processing() -> list[dict]:
    """List of rows currently being processed — for live ticker display."""
    df = read_state()
    if df.empty:
        return []
    rows = df[df["status"].isin(["in_progress", "processing"])]
    return rows.to_dict(orient="records")


_LOG_NOISE_PATTERNS = (
    "no stdin data received",
    "If piping from a slow command",
)


def latest_log_tail(n_lines: int = 8) -> tuple[str, str]:
    """Returns (log_filename, last_n_lines) from the most recent batch log,
    filtered to drop known harmless warnings (claude -p stdin warning, etc.)."""
    from pathlib import Path
    logs_dir = project_root() / "batch" / "logs"
    if not logs_dir.exists():
        return "", ""
    log_files = [p for p in logs_dir.glob("*.log") if p.is_file()]
    if not log_files:
        return "", ""
    latest = max(log_files, key=lambda p: p.stat().st_mtime)
    try:
        raw = latest.read_text(encoding="utf-8", errors="ignore").splitlines()
    except Exception:
        return latest.name, ""
    filtered = [ln for ln in raw if not any(p in ln for p in _LOG_NOISE_PATTERNS)]
    if not filtered:
        # If everything got filtered, fall back to "running cleanly" so the
        # user knows the worker is alive.
        filtered = ["(worker is running — no output yet)"]
    return latest.name, "\n".join(filtered[-n_lines:])
