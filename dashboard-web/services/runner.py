"""Subprocess wrapper around the existing .mjs scripts.

Every shellout goes through here so the Streamlit pages can stay
declarative and we have one place to add logging, timeouts, and
error handling.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional, Sequence

from . import project_root

try:
    import yaml  # type: ignore
except Exception:  # pragma: no cover - yaml ships with the dashboard deps
    yaml = None


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


# ── WebSearch scan (LLM-driven, via `claude -p`) ───────────────────────
# The zero-token engine (scan.mjs) only reaches ATS APIs. This path uses
# Claude + WebSearch to cover the `search_queries` in portals.yml (LinkedIn,
# eFinancialCareers, recruiters…) that have no public API. It costs Claude
# tokens, so the UI gates it behind an explicit opt-in.

WEBSEARCH_DEFAULT_MAX_QUERIES = 8

# Hard override so the headless run can't get hijacked by the repo's career-ops
# skill (which otherwise asks a clarifying AskUserQuestion and returns nothing).
WEBSEARCH_SYSTEM = (
    "You are a headless job-posting scraper running non-interactively. "
    "You MUST NOT ask clarifying questions and MUST NOT use the AskUserQuestion tool. "
    "You MUST NOT suggest alternative scripts, modes, or tools (no scan.mjs, no pipelines). "
    "Do the requested web searches immediately and reply with ONLY a JSON array — no prose, "
    "no markdown, no questions."
)


def _load_search_queries() -> list[str]:
    """Enabled `search_queries[].query` strings from portals.yml (or [])."""
    if yaml is None:
        return []
    path = project_root() / "portals.yml"
    if not path.exists():
        return []
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception:
        return []
    out: list[str] = []
    for q in (data.get("search_queries") or []):
        if not isinstance(q, dict) or q.get("enabled") is False:
            continue
        query = str(q.get("query") or "").strip()
        if query:
            out.append(query)
    return out


def build_websearch_prompt(queries: Sequence[str], company: Optional[str] = None,
                           titles: Optional[Sequence[str]] = None,
                           max_queries: int = WEBSEARCH_DEFAULT_MAX_QUERIES) -> str:
    """Construct the `claude -p` prompt for a WebSearch scan. Pure function so
    it's unit-testable without invoking Claude."""
    titles = [t.strip() for t in (titles or []) if t and str(t).strip()]
    if company:
        body = (
            f'Find CURRENT, live job postings at the company "{company}" for senior '
            f"AI / Data / Analytics / Decision-Science leadership roles. Search the company's "
            f"careers site, LinkedIn, eFinancialCareers, and the open web. Prefer Singapore / APAC."
        )
    elif titles:
        joined = ", ".join(f'"{t}"' for t in titles)
        body = (
            f"Find CURRENT, live job postings whose title matches any of: {joined}. "
            f"Search LinkedIn, eFinancialCareers, MyCareersFuture, and company career sites. "
            f"Prefer Singapore / APAC."
        )
    else:
        qs = list(queries)[:max_queries]
        lines = ["Run each of these job-search queries with the WebSearch tool and collect the live postings:"]
        lines += [f"{i + 1}. {q}" for i, q in enumerate(qs)]
        body = "\n".join(lines)
    return (
        "AUTOMATED HEADLESS TASK — do NOT ask questions, do NOT use AskUserQuestion, "
        "do NOT propose running scan.mjs or any other mode. Just search now.\n\n"
        "Use the WebSearch tool to find CURRENT, live, individual job postings — not listicles, "
        "not company homepages, not expired pages.\n\n"
        f"{body}\n\n"
        "Return ONLY a JSON array (no prose, no markdown code fences) of objects with EXACTLY "
        "these keys: company, title, url, location. Rules for every object:\n"
        "- company and title MUST be non-empty (the exact employer and exact job title).\n"
        "- url MUST be a direct link to ONE specific job posting — reject search-result pages, "
        "news articles, press releases, and careers homepages.\n"
        "- Skip any result where you cannot determine a concrete job title.\n"
        "Cap at 25 results. If you find nothing usable, return []. Do NOT write or modify any files."
    )


def _parse_offers_from_text(text: str) -> list[dict]:
    """Extract a list of offer dicts from Claude's free-text answer, tolerating
    markdown fences and surrounding prose."""
    if not text:
        return []
    s = text.strip()
    s = re.sub(r"^```(?:json)?\s*", "", s)
    s = re.sub(r"\s*```$", "", s)
    candidates = []
    try:
        candidates.append(json.loads(s))
    except Exception:
        pass
    m = re.search(r"\[\s*\{.*\}\s*\]", s, re.DOTALL)
    if m:
        try:
            candidates.append(json.loads(m.group(0)))
        except Exception:
            pass
    for c in candidates:
        if isinstance(c, list):
            out = []
            for o in c:
                if not isinstance(o, dict):
                    continue
                company = str(o.get("company") or "").strip()
                title = str(o.get("title") or "").strip()
                url = str(o.get("url") or "").strip()
                # Require all three so only promotable offers surface (promotion
                # needs company + role, and an offer with no URL isn't actionable).
                if url and title and company:
                    out.append({
                        "company": company,
                        "title": title,
                        "url": url,
                        "location": str(o.get("location") or "").strip(),
                        "source": "websearch",
                    })
            return out
    return []


def websearch_scan(company: Optional[str] = None, titles: Optional[Sequence[str]] = None,
                   timeout: int = 900) -> dict:
    """Run a WebSearch-based scan via `claude -p` and return a summary dict in
    the same shape the scan dialog consumes (ok / new_offers / offers / errors).
    Always returns a dict — never raises — so the UI can render failures."""
    from .batch import find_claude

    claude = find_claude()
    if not claude:
        return {"ok": False, "new_offers": 0, "offers": [], "hint": "no-claude",
                "errors": [{"company": "claude", "error": "claude CLI not found on PATH"}]}

    queries = _load_search_queries()
    if not (company or titles) and not queries:
        return {"ok": False, "new_offers": 0, "offers": [],
                "errors": [{"company": "scan", "error": "no search_queries configured in portals.yml"}]}

    prompt = build_websearch_prompt(queries, company=company, titles=titles)
    args = [
        claude, "-p", "--dangerously-skip-permissions",
        "--disallowed-tools", "AskUserQuestion",
        "--append-system-prompt", WEBSEARCH_SYSTEM,
        "--output-format", "json", prompt,
    ]
    try:
        proc = subprocess.run(
            args, cwd=str(project_root()), capture_output=True, text=True,
            timeout=timeout, encoding="utf-8", errors="replace",
        )
    except subprocess.TimeoutExpired:
        return {"ok": False, "new_offers": 0, "offers": [],
                "errors": [{"company": "claude", "error": f"WebSearch scan timed out after {timeout}s"}]}
    except OSError as exc:
        return {"ok": False, "new_offers": 0, "offers": [],
                "errors": [{"company": "claude", "error": f"failed to launch claude: {exc}"}]}

    raw = proc.stdout or ""
    result_text = raw
    # `claude -p --output-format json` wraps the answer in {"result": "..."}.
    try:
        env = json.loads(raw.strip())
        if isinstance(env, dict) and "result" in env:
            result_text = env.get("result") or ""
    except Exception:
        pass

    offers = _parse_offers_from_text(result_text)
    ok = proc.returncode == 0
    return {
        "ok": ok,
        "new_offers": len(offers),
        "offers": offers,
        "errors": [] if ok else [{"company": "claude", "error": (proc.stderr or "claude exited non-zero")[:500]}],
        "_raw_stdout": raw[-4000:],
        "_raw_stderr": (proc.stderr or "")[-2000:],
        "_returncode": proc.returncode,
    }


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
