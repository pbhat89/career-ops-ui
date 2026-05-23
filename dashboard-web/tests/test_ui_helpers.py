"""Tests for services.ui_helpers — NaN-safe getters and badge HTML."""

from __future__ import annotations

import math

from services.ui_helpers import (
    safe_str, has_value, score_tier, score_verdict,
    status_badge_html, score_badge_html,
    pill_html, kpi_tile_html, kpi_tile_grid,
    section_header_html, status_strip_html, verdict_card_html,
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
    # Low-fit colors live in the red family — exact hex shifts between palette revisions
    assert score_tier(2.0).lower() in {"#fda4af", "#f87171"}


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


# ── score_verdict ─────────────────────────────────────────────────────

def test_score_verdict_none():
    label, fg, bg, bd = score_verdict(None)
    assert "Not scored" in label
    assert fg.startswith("#")


def test_score_verdict_strong():
    label, fg, _, _ = score_verdict(4.7)
    assert "Strong" in label
    assert fg.lower() in {"#44d49a", "#3db985"}


def test_score_verdict_borderline():
    label, _, _, _ = score_verdict(3.6)
    assert "Borderline" in label


def test_score_verdict_low():
    label, _, _, _ = score_verdict(2.0)
    assert "Low fit" in label or "skip" in label.lower()


# ── pill_html ─────────────────────────────────────────────────────────

def test_pill_html_default_variant():
    html = pill_html("hello")
    assert 'class="pill pill-default"' in html
    assert ">hello<" in html


def test_pill_html_known_variants():
    for variant in ("accent", "info", "warn", "danger", "success", "violet", "muted"):
        html = pill_html("x", variant)
        assert f"pill-{variant}" in html


def test_pill_html_unknown_variant_falls_back_to_default():
    html = pill_html("x", "nonsense")
    assert "pill-default" in html


def test_pill_html_with_dot():
    html = pill_html("x", "accent", dot=True)
    assert "pill-dot" in html


def test_pill_html_without_dot():
    html = pill_html("x", "accent", dot=False)
    assert "pill-dot" not in html


# ── kpi_tile_html / kpi_tile_grid ─────────────────────────────────────

def test_kpi_tile_html_renders_label_and_value():
    html = kpi_tile_html("Jobs", 42)
    assert "Jobs" in html
    assert ">42<" in html
    assert "kpi-tile-value" in html
    assert "accent" not in html  # not flagged accent


def test_kpi_tile_html_accent_flag():
    html = kpi_tile_html("Hot", 7, accent=True)
    assert "kpi-tile-value accent" in html


def test_kpi_tile_grid_renders_all_items():
    html = kpi_tile_grid([
        ("A", 1, False),
        ("B", 2, True),
        ("C", 3, False),
    ])
    assert "kpi-tile-grid" in html
    for lbl in ("A", "B", "C"):
        assert lbl in html
    # exactly one tile should be flagged accent
    assert html.count("value accent") == 1


# ── section_header_html ───────────────────────────────────────────────

def test_section_header_title_only():
    html = section_header_html("Worklist")
    assert "Worklist" in html
    assert "sh-desc" not in html
    assert "sh-badge" not in html


def test_section_header_with_description_and_badge():
    html = section_header_html("Worklist", description="Pick a role", badge="42")
    assert "Worklist" in html
    assert "Pick a role" in html
    assert "sh-badge" in html
    assert ">42<" in html


# ── status_strip_html ─────────────────────────────────────────────────

def test_status_strip_no_progress_bar_when_none():
    html = status_strip_html("Batch", "3/5 — running", [("Active", 2)])
    assert "Batch" in html
    assert "3/5 — running" in html
    assert "Active" in html
    assert ">2<" in html
    assert "status-strip-bar-fill" not in html


def test_status_strip_with_progress_bar():
    html = status_strip_html("Batch", "head", [("X", 1)], progress=0.75)
    assert "status-strip-bar-fill" in html
    assert "width:75.0%" in html


def test_status_strip_progress_clamps():
    html_low = status_strip_html("B", "h", [], progress=-0.5)
    html_hi = status_strip_html("B", "h", [], progress=1.5)
    assert "width:0.0%" in html_low
    assert "width:100.0%" in html_hi


# ── verdict_card_html ─────────────────────────────────────────────────

def test_verdict_card_includes_label_and_score():
    html = verdict_card_html(4.6, "Solid fit on skills + comp.")
    assert "Strong fit" in html
    assert "4.6/5" in html
    assert "Solid fit on skills" in html


def test_verdict_card_handles_none_score():
    html = verdict_card_html(None, "")
    assert "Not scored" in html
    assert "—" in html or "—" in html
    # Empty TL;DR should fall back to the safe_str default
    assert "No TL;DR" in html
