"""Subprocess wrapper around the existing .mjs scripts.

Every shellout goes through here so the Streamlit pages can stay
declarative and we have one place to add logging, timeouts, and
error handling.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional, Sequence

from . import project_root


@dataclass
class RunResult:
    ok: bool
    stdout: str
    stderr: str
    returncode: int

    def json(self):
        """Parse the FIRST valid JSON object on stdout (forgiving of preamble)."""
        s = (self.stdout or "").strip()
        if not s:
            return None
        try:
            return json.loads(s)
        except Exception:
            pass
        # Look for the last JSON-looking line — handy when callers print warnings.
        for line in reversed(s.splitlines()):
            line = line.strip()
            if line.startswith("{") and line.endswith("}"):
                try:
                    return json.loads(line)
                except Exception:
                    continue
        return None


def _node() -> str:
    for candidate in ("node", "node.exe"):
        path = shutil.which(candidate)
        if path:
            return path
    raise RuntimeError("node executable not found on PATH")


def _run(args: list[str], timeout: int = 300, cwd: Optional[Path] = None) -> RunResult:
    try:
        proc = subprocess.run(
            args,
            cwd=str(cwd or project_root()),
            capture_output=True,
            text=True,
            timeout=timeout,
            encoding="utf-8",
            errors="replace",
        )
    except subprocess.TimeoutExpired as exc:
        return RunResult(
            ok=False,
            stdout=(exc.stdout or "") if isinstance(exc.stdout, str) else "",
            stderr=f"Timed out after {timeout}s: {' '.join(args)}",
            returncode=124,
        )
    except FileNotFoundError as exc:
        return RunResult(False, "", f"Executable not found: {exc}", 127)
    except OSError as exc:
        return RunResult(False, "", f"Failed to launch process: {exc}", 1)
    return RunResult(
        ok=proc.returncode == 0,
        stdout=proc.stdout or "",
        stderr=proc.stderr or "",
        returncode=proc.returncode,
    )


def run_script(script: str, *args: str, timeout: int = 300) -> RunResult:
    root = project_root()
    script_path = root / script
    if not script_path.exists():
        return RunResult(False, "", f"Script not found: {script}", 127)
    try:
        node_path = _node()
    except RuntimeError as exc:
        return RunResult(False, "", str(exc), 127)
    return _run([node_path, str(script_path), *args], timeout=timeout)


# ── High-level wrappers used by pages ──────────────────────────────────

def _scan_args(dry_run: bool, company: Optional[str], titles: Optional[Sequence[str]],
               json_out: bool) -> list[str]:
    args: list[str] = []
    if dry_run:
        args.append("--dry-run")
    if company:
        args.extend(["--company", company.strip()])
    for t in (titles or []):
        t = (t or "").strip()
        if t:
            args.extend(["--title", t])
    if json_out:
        args.append("--json")
    return args


def scan(dry_run: bool = False, company: Optional[str] = None,
         titles: Optional[Sequence[str]] = None, json_out: bool = False) -> RunResult:
    return run_script("scan.mjs", *_scan_args(dry_run, company, titles, json_out), timeout=600)


def _fallback_summary(result: RunResult) -> dict:
    return {
        "ok": result.ok,
        "errors": [{"company": "scan", "error": result.stderr.strip() or "no JSON returned"}],
        "new_offers": 0,
        "companies_scanned": 0,
        "total_found": 0,
        "filtered": 0,
        "duplicates": 0,
        "offers": [],
    }


def scan_summary(dry_run: bool = False, company: Optional[str] = None,
                 titles: Optional[Sequence[str]] = None) -> dict:
    """Run scan.mjs --json and return its parsed summary. Always returns a dict
    so callers don't have to defensively check None — `ok` is False on failure."""
    result = scan(dry_run=dry_run, company=company, titles=titles, json_out=True)
    payload = result.json()
    if not isinstance(payload, dict):
        payload = _fallback_summary(result)
    payload["_raw_stdout"] = (result.stdout or "")[-4000:]
    payload["_raw_stderr"] = (result.stderr or "")[-4000:]
    payload["_returncode"] = result.returncode
    return payload


def scan_stream(
    on_line: Callable[[str], None],
    dry_run: bool = False,
    company: Optional[str] = None,
    titles: Optional[Sequence[str]] = None,
    timeout: int = 600,
) -> dict:
    """Run `scan.mjs --json`, streaming live progress lines (stderr) to `on_line`
    as they arrive, while capturing the JSON summary (stdout) in full.

    Returns the same dict shape as `scan_summary`. This powers the live
    TQDM-style log in the scan dialog: each company emits a `[k/N] ✓ …` line
    on stderr the moment it completes; the single JSON object lands on stdout
    at the end.
    """
    root = project_root()
    script_path = root / "scan.mjs"
    if not script_path.exists():
        return _fallback_summary(RunResult(False, "", "scan.mjs not found", 127))
    try:
        node_path = _node()
    except RuntimeError as exc:
        return _fallback_summary(RunResult(False, "", str(exc), 127))

    args = [node_path, str(script_path), *_scan_args(dry_run, company, titles, json_out=True)]
    try:
        proc = subprocess.Popen(
            args,
            cwd=str(root),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
        )
    except (OSError, FileNotFoundError) as exc:
        return _fallback_summary(RunResult(False, "", f"Failed to launch scan: {exc}", 1))

    # Drain stdout in a thread so a full pipe buffer can never deadlock the
    # stderr reader (the JSON blob is small, but be safe).
    stdout_chunks: list[str] = []

    def _drain_stdout() -> None:
        assert proc.stdout is not None
        for chunk in proc.stdout:
            stdout_chunks.append(chunk)

    t = threading.Thread(target=_drain_stdout, daemon=True)
    t.start()

    stderr_lines: list[str] = []
    try:
        assert proc.stderr is not None
        for raw in proc.stderr:
            line = raw.rstrip("\n")
            if not line:
                continue
            stderr_lines.append(line)
            try:
                on_line(line)
            except Exception:
                pass
        proc.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        proc.kill()
        return _fallback_summary(RunResult(False, "", f"Scan timed out after {timeout}s", 124))
    finally:
        t.join(timeout=5)

    result = RunResult(
        ok=proc.returncode == 0,
        stdout="".join(stdout_chunks),
        stderr="\n".join(stderr_lines),
        returncode=proc.returncode or 0,
    )
    payload = result.json()
    if not isinstance(payload, dict):
        payload = _fallback_summary(result)
    payload["_raw_stdout"] = (result.stdout or "")[-4000:]
    payload["_raw_stderr"] = (result.stderr or "")[-4000:]
    payload["_returncode"] = result.returncode
    return payload


def check_liveness(urls: list[str]) -> RunResult:
    if not urls:
        return RunResult(True, "", "", 0)
    return run_script("check-liveness.mjs", *urls, timeout=60 + 15 * len(urls))


def analyze_patterns() -> RunResult:
    return run_script("analyze-patterns.mjs", timeout=120)


def followup_cadence() -> RunResult:
    return run_script("followup-cadence.mjs", timeout=60)


def merge_tracker() -> RunResult:
    return run_script("merge-tracker.mjs", timeout=60)


def doctor() -> RunResult:
    return run_script("doctor.mjs", timeout=60)


def verify_pipeline() -> RunResult:
    return run_script("verify-pipeline.mjs", timeout=60)


def generate_pdf(slug: Optional[str] = None) -> RunResult:
    args = [slug] if slug else []
    return run_script("generate-pdf.mjs", *args, timeout=180)


def generate_latex(slug: Optional[str] = None) -> RunResult:
    """Generate the LaTeX/Overleaf .tex variant of the CV."""
    args = [slug] if slug else []
    return run_script("generate-latex.mjs", *args, timeout=120)


def normalize_statuses(dry_run: bool = True) -> RunResult:
    args = ["--dry-run"] if dry_run else []
    return run_script("normalize-statuses.mjs", *args, timeout=60)


def dedup_tracker(dry_run: bool = True) -> RunResult:
    args = ["--dry-run"] if dry_run else []
    return run_script("dedup-tracker.mjs", *args, timeout=60)


def update_check() -> RunResult:
    return run_script("update-system.mjs", "check", timeout=30)


def update_apply() -> RunResult:
    return run_script("update-system.mjs", "apply", timeout=120)
