"""Cold-start auto-refresh orchestrator.

When the user opens the app after days away, we want to:
  1. Re-scan portals if last scan > N days
  2. Liveness-check JD URLs on active applications
  3. Recompute follow-up cadence
  4. Re-run pattern analysis

This module returns a plan that the UI can execute step-by-step,
showing live progress in a Streamlit st.status panel.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from . import project_root
from . import runner, tracker

DEFAULT_SCAN_INTERVAL_DAYS = 3
DEFAULT_LIVENESS_INTERVAL_DAYS = 7
ACTIVE_STATUSES = {"Applied", "Responded", "Interview"}

LAST_REFRESH_MARKER = "data/.last-refresh"


@dataclass
class RefreshStep:
    name: str
    description: str
    action: Callable[[], dict]


def _scan_age_days() -> float:
    path = project_root() / "data" / "scan-history.tsv"
    if not path.exists():
        return 999.0
    age = dt.datetime.now() - dt.datetime.fromtimestamp(path.stat().st_mtime)
    return age.total_seconds() / 86400.0


def _last_refresh_age_days() -> float:
    path = project_root() / LAST_REFRESH_MARKER
    if not path.exists():
        return 999.0
    age = dt.datetime.now() - dt.datetime.fromtimestamp(path.stat().st_mtime)
    return age.total_seconds() / 86400.0


def _mark_refresh() -> None:
    path = project_root() / LAST_REFRESH_MARKER
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dt.datetime.now().isoformat(), encoding="utf-8")


def _do_scan() -> dict:
    age = _scan_age_days()
    if age < DEFAULT_SCAN_INTERVAL_DAYS:
        return {"skipped": True, "reason": f"last scan {age:.1f}d ago"}
    result = runner.scan()
    return {
        "ok": result.ok,
        "summary": (result.stdout or result.stderr).strip().splitlines()[-5:],
    }


def _do_liveness() -> dict:
    df = tracker.load_applications()
    if df.empty:
        return {"checked": 0}
    active = df[df["status"].isin(ACTIVE_STATUSES) & df["job_url"].notna()]
    urls = active["job_url"].dropna().unique().tolist()
    if not urls:
        return {"checked": 0}
    # Cap at 20 to keep cold-start under control
    urls = urls[:20]
    result = runner.check_liveness(urls)
    return {
        "ok": result.ok,
        "checked": len(urls),
        "tail": (result.stdout or result.stderr).strip().splitlines()[-10:],
    }


def _do_followup() -> dict:
    result = runner.followup_cadence()
    payload = result.json() or {}
    overdue = []
    if isinstance(payload, dict):
        overdue = payload.get("overdue", []) or []
    return {"ok": result.ok, "overdue_count": len(overdue)}


def _do_patterns() -> dict:
    result = runner.analyze_patterns()
    payload = result.json() or {}
    pattern_count = 0
    if isinstance(payload, dict):
        pattern_count = len(payload.get("patterns", []) or [])
    return {"ok": result.ok, "patterns": pattern_count}


def first_launch() -> bool:
    """True if the dashboard has never been opened on this machine.
    We skip auto-refresh on first launch so the user sees their existing
    data immediately — they can trigger a refresh manually."""
    return not (project_root() / LAST_REFRESH_MARKER).exists()


def should_auto_refresh() -> bool:
    """Auto-refresh kicks in only if we've been opened before AND it's
    been at least 1 day since the last refresh."""
    if first_launch():
        return False
    return _last_refresh_age_days() >= 1.0


def build_plan(force: bool = False) -> list[RefreshStep]:
    """Return the list of steps to run on cold start."""
    plan: list[RefreshStep] = []

    if force or should_auto_refresh():
        plan.append(RefreshStep(
            name="Re-scan portals",
            description=f"Hits Greenhouse/Ashby/Lever if last scan > {DEFAULT_SCAN_INTERVAL_DAYS}d",
            action=_do_scan,
        ))
        plan.append(RefreshStep(
            name="Liveness check",
            description="Verifies JDs on active applications are still posted",
            action=_do_liveness,
        ))
        plan.append(RefreshStep(
            name="Follow-up cadence",
            description="Recomputes who is due for a nudge",
            action=_do_followup,
        ))
        plan.append(RefreshStep(
            name="Pattern analysis",
            description="Refreshes rejection patterns and archetype performance",
            action=_do_patterns,
        ))
    return plan


def run_plan(plan: list[RefreshStep], on_step=None) -> list[tuple[str, dict]]:
    results: list[tuple[str, dict]] = []
    for step in plan:
        if on_step:
            on_step(step.name, "running")
        try:
            outcome = step.action()
        except Exception as e:
            outcome = {"ok": False, "error": str(e)}
        results.append((step.name, outcome))
        if on_step:
            on_step(step.name, "done", outcome)
    _mark_refresh()
    return results
