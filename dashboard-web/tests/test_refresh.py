"""Tests for services.refresh — first-launch + auto-refresh gating."""

from __future__ import annotations

import datetime as dt

from services import refresh


def test_first_launch_true_when_no_marker(temp_root):
    assert refresh.first_launch() is True


def test_first_launch_false_after_mark(temp_root):
    refresh._mark_refresh()
    assert refresh.first_launch() is False


def test_should_auto_refresh_false_on_first_launch(temp_root):
    assert refresh.should_auto_refresh() is False


def test_should_auto_refresh_false_if_recent(temp_root):
    refresh._mark_refresh()
    assert refresh.should_auto_refresh() is False


def test_build_plan_empty_on_first_launch(temp_root):
    plan = refresh.build_plan()
    assert plan == []


def test_build_plan_force_returns_four_steps(temp_root):
    plan = refresh.build_plan(force=True)
    assert len(plan) == 4
    names = [s.name for s in plan]
    assert "Re-scan portals" in names
    assert "Liveness check" in names
    assert "Follow-up cadence" in names
    assert "Pattern analysis" in names


def test_run_plan_marks_refresh(temp_root):
    # No-op steps so we don't actually shell out
    def _noop():
        return {"ok": True}
    plan = [refresh.RefreshStep("test", "test", _noop)]
    refresh.run_plan(plan)
    assert refresh.first_launch() is False
