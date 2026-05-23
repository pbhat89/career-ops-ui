"""Tests for services.ui_helpers — NaN-safe getters and badge HTML."""

from __future__ import annotations

import math

from services.ui_helpers import (
    safe_str, has_value, score_tier, status_badge_html, score_badge_html,
)


def test_safe_str_handles_none():
    assert safe_str(None) == ""
    assert safe_str(None, default="x") == "x"


def test_safe_str_handles_nan():
    assert safe_str(float("nan")) == ""
    assert safe_str(math.nan, default="-") == "-"


def test_safe_str_strips_whitespace():
    assert safe_str("  hello  ") == "hello"


def test_safe_str_lowercase_nan_string():
    assert safe_str("nan") == ""
    assert safe_str("None") == ""


def test_has_value():
    assert has_value("x") is True
    assert has_value(None) is False
    assert has_value(float("nan")) is False
    assert has_value("") is False
    assert has_value("   ") is False


def test_score_tier_returns_color_for_high():
    assert score_tier(4.6).startswith("#")
    # Accent green can shift between palette revisions — assert the family,
    # not the exact hex.
    assert score_tier(5.0).lower() in {"#3db985", "#44d49a", "#34b27f"}
    assert score_tier(4.0) == "#6EE7B7"  # soft green


def test_score_tier_neutral_for_none():
    assert score_tier(None) == "#8C9196"
    assert score_tier(float("nan")) == "#8C9196"


def test_score_tier_red_for_low():
    assert score_tier(2.0) == "#FDA4AF"


def test_status_badge_includes_in_progress():
    html = status_badge_html("In progress")
    assert "In progress" in html
    # In-progress should use amber/yellow, not the default gray
    assert "FBBF24" in html or "fbbf24" in html.lower()


def test_status_badge_html_contains_label():
    html = status_badge_html("Applied")
    assert "Applied" in html
    assert "<span" in html


def test_status_badge_html_handles_unknown():
    html = status_badge_html("Unknown-Custom-Status")
    assert "Unknown-Custom-Status" in html


def test_score_badge_handles_none():
    html = score_badge_html(None)
    assert "–" in html


def test_score_badge_handles_value():
    html = score_badge_html(4.2)
    assert "4.2/5" in html
