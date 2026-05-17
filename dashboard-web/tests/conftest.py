"""Pytest setup — fixture for a temporary career-ops project root.

Each test that needs to read/write tracker/reports/scan data uses the
`temp_root` fixture, which builds a minimal valid layout in tmp_path and
monkeypatches services.project_root() to point at it.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Make `services` importable from the test files
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))


APPLICATIONS_FIXTURE = """# Applications Tracker

| # | Date | Company | Role | Score | Status | PDF | Report | Notes |
|---|------|---------|------|-------|--------|-----|--------|-------|
| 1 | 2026-05-02 | HSBC | Head of DAO Singapore | 4.5/5 | Evaluated | ✅ | [001](reports/001-hsbc-2026-05-02.md) | Posting expired — apply on next reposting. |
| 2 | 2026-05-02 | SMBC | MD, Data & Analytics CoE | 4.1/5 | Applied | ✅ | [002](reports/002-smbc-2026-05-02.md) | Verify posting active. |
| 3 | 2026-05-02 | JPMorgan APAC | Head of AI Products | -/5 | Pending | ❌ | - | URL: https://example.com/jpm |
| 4 | 2026-05-16 | Nomura | VP Data Science | -/5 | Pending | ❌ | - | No URL yet. |
| 5 | 2026-05-16 | GIC | Lead DS | -/5 | Discarded | ❌ | - | CLOSED 2020-08-26 (stale). |
"""

REPORT_FIXTURE = """# Evaluation: HSBC — Head of DAO Singapore

**Date:** 2026-05-02
**Archetype:** Head of Analytics / Data
**Score:** 4.5/5
**Legitimacy:** Expired (apply on next reposting)
**URL:** https://example.com/hsbc-dao
**PDF:** output/cv-hsbc-2026-05-02.pdf
**Cover letter:** output/cover-letter-hsbc-2026-05-02.md

---

## A) Role Summary

| Field | Value |
|-------|-------|
| **TL;DR** | Run data strategy across HSBC's SG/MY/ID cluster. |
"""


@pytest.fixture
def temp_root(tmp_path, monkeypatch):
    """Build a minimal career-ops project root in tmp_path."""
    (tmp_path / "data").mkdir()
    (tmp_path / "reports").mkdir()
    (tmp_path / "config").mkdir()
    (tmp_path / "batch").mkdir()
    (tmp_path / "batch" / "logs").mkdir()
    (tmp_path / "batch" / "tracker-additions").mkdir()

    (tmp_path / "data" / "applications.md").write_text(APPLICATIONS_FIXTURE, encoding="utf-8")
    (tmp_path / "reports" / "001-hsbc-2026-05-02.md").write_text(REPORT_FIXTURE, encoding="utf-8")
    (tmp_path / "data" / "scan-history.tsv").write_text(
        "url\tfirst_seen\tportal\ttitle\tcompany\tstatus\n"
        "https://example.com/a\t2026-05-16\tgreenhouse\tHead of AI\tFooCorp\tadded\n"
        "https://example.com/b\t2026-05-16\tashby\tDir DS\tBarCorp\tadded\n"
        "https://example.com/c\t2026-05-15\tlever\tLead DS\tBazCorp\tskipped_expired\n",
        encoding="utf-8",
    )

    # Monkeypatch project_root() across all service modules
    import services
    monkeypatch.setattr(services, "project_root", lambda: tmp_path)
    import services.tracker
    monkeypatch.setattr(services.tracker, "project_root", lambda: tmp_path)
    import services.reports
    monkeypatch.setattr(services.reports, "project_root", lambda: tmp_path)
    import services.batch
    monkeypatch.setattr(services.batch, "project_root", lambda: tmp_path)
    import services.refresh
    monkeypatch.setattr(services.refresh, "project_root", lambda: tmp_path)
    import services.runner
    monkeypatch.setattr(services.runner, "project_root", lambda: tmp_path)
    import services.single_eval
    monkeypatch.setattr(services.single_eval, "project_root", lambda: tmp_path)

    return tmp_path
