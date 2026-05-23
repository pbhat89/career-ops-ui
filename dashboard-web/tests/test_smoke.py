"""Smoke tests — boot each page and the services package without crashing.

Uses streamlit.testing.v1.AppTest to drive the app headlessly. If the page
imports or top-level code raises, the test fails with a real traceback.
"""

from __future__ import annotations

import importlib
from pathlib import Path

import pytest

# ── Service-layer smoke (no Streamlit context needed) ─────────────────


def test_services_import_cleanly():
    """Every service module must import without side effects."""
    for name in (
        "services",
        "services.tracker",
        "services.reports",
        "services.runner",
        "services.batch",
        "services.refresh",
        "services.single_eval",
        "services.styling",
        "services.ui_helpers",
        "services.interest",
    ):
        mod = importlib.import_module(name)
        assert mod is not None


def test_styling_injects_without_error(monkeypatch):
    """styling.inject() should produce valid CSS even outside a script run."""
    from services import styling

    captured = {}

    def fake_md(html, unsafe_allow_html=False):
        captured["html"] = html
        captured["unsafe"] = unsafe_allow_html

    monkeypatch.setattr("streamlit.markdown", fake_md)
    styling.inject()
    assert captured.get("unsafe") is True
    # Inter is the UI font in the shadcn-style revamp (was Outfit pre-v2)
    assert "Inter" in captured["html"]
    assert "#44D49A" in captured["html"]     # brighter accent green (post-revamp)
    assert "row-progress" in captured["html"]  # per-row progress class
    assert "action-card" in captured["html"]   # the card grid CSS
    # Tiles and pills introduced in the shadcn-style revamp
    assert "kpi-tile" in captured["html"]
    assert "pill pill-default" in captured["html"] or "pill-default" in captured["html"]


def test_runner_helpers_exist():
    """Every helper exposed for the dashboard should be importable + callable."""
    from services import runner
    for fn in (
        "scan", "scan_summary", "check_liveness", "analyze_patterns",
        "followup_cadence", "merge_tracker", "doctor", "verify_pipeline",
        "generate_pdf", "generate_latex",
        "normalize_statuses", "dedup_tracker",
        "update_check", "update_apply",
    ):
        assert callable(getattr(runner, fn)), f"runner.{fn} missing or not callable"


# ── Page-level smoke (AppTest — drives the full Streamlit script) ─────


PAGES = ["pages/desk.py", "pages/role.py", "pages/signals.py"]


def _can_run_apptest() -> bool:
    try:
        from streamlit.testing.v1 import AppTest  # noqa: F401
        return True
    except Exception:
        return False


@pytest.mark.parametrize("page", PAGES)
def test_page_boots_without_exception(page, temp_root, monkeypatch):
    """Each top-level page should run end-to-end against the fixture tree."""
    if not _can_run_apptest():
        pytest.skip("streamlit.testing.v1.AppTest not available in this Streamlit version")
    from streamlit.testing.v1 import AppTest

    # The pages import `services` which uses Path(__file__).parent.parent.parent —
    # we need the AppTest to point at the real dashboard-web/pages/*.py file,
    # then monkeypatch project_root to the fixture.
    project_root_dash = Path(__file__).resolve().parent.parent  # dashboard-web/
    page_path = project_root_dash / page
    if not page_path.exists():
        pytest.skip(f"{page} not found")

    at = AppTest.from_file(str(page_path), default_timeout=20)
    # Point the services layer at the fixture project root for the duration
    # of the run.
    import services
    monkeypatch.setattr(services, "project_root", lambda: temp_root)

    at.run()

    # The fixture tracker has 5 rows; the pages should not crash. Any unhandled
    # exception lands on at.exception — assert it's empty.
    assert not at.exception, [str(e) for e in at.exception]
