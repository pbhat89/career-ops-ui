"""Tiny presentational helpers — color tiers, badges, NaN-safe getters."""

from __future__ import annotations

import math
from typing import Any

import pandas as pd


# ── NaN-safe getters ──────────────────────────────────────────────────

def safe_str(value: Any, default: str = "") -> str:
    """Return a clean string; convert NaN / None / 'nan' to default."""
    if value is None:
        return default
    if isinstance(value, float) and math.isnan(value):
        return default
    if pd.isna(value):
        return default
    s = str(value).strip()
    if s.lower() in ("nan", "none", ""):
        return default
    return s


def has_value(value: Any) -> bool:
    return safe_str(value, "") != ""


# ── Score color tier ──────────────────────────────────────────────────

def score_tier(score: float | None) -> str:
    """Return a CSS color for a score on a 5-point scale."""
    if score is None or (isinstance(score, float) and math.isnan(score)):
        return "#8C9196"  # neutral
    if score >= 4.5:
        return "#44D49A"  # accent green
    if score >= 4.0:
        return "#6EE7B7"  # soft green
    if score >= 3.5:
        return "#FDBA74"  # amber
    if score >= 3.0:
        return "#FB923C"  # orange
    return "#FDA4AF"      # red


# ── Status color tier ─────────────────────────────────────────────────

_STATUS_COLORS = {
    "Pending":     ("#8C9196", "rgba(140,145,150,0.10)"),
    "Watchlist":   ("#C4B5FD", "rgba(196,181,253,0.12)"),
    "Evaluated":   ("#3DB985", "rgba(61,185,133,0.14)"),
    "In progress": ("#FBBF24", "rgba(251,191,36,0.12)"),
    "Applied":     ("#5385C6", "rgba(83,133,198,0.14)"),
    "Responded":   ("#FDBA74", "rgba(253,186,116,0.12)"),
    "Interview":   ("#6EE7B7", "rgba(110,231,183,0.14)"),
    "Offer":       ("#3DB985", "rgba(61,185,133,0.18)"),
    "Rejected":    ("#FDA4AF", "rgba(253,164,175,0.12)"),
    "Discarded":   ("#62666D", "rgba(98,102,109,0.10)"),
    "SKIP":        ("#62666D", "rgba(98,102,109,0.10)"),
    "Failed":      ("#FDA4AF", "rgba(253,164,175,0.12)"),
}


def status_badge_html(status: str) -> str:
    fg, bg = _STATUS_COLORS.get(status, ("#6b7280", "rgba(107,114,128,0.10)"))
    label = safe_str(status, "?")
    return (
        f'<span style="display:inline-block;padding:3px 10px;border-radius:999px;'
        f'font-size:0.72rem;font-weight:600;color:{fg};background:{bg};'
        f'border:1px solid {fg}33;letter-spacing:0.02em;">{label}</span>'
    )


def score_badge_html(score: float | None) -> str:
    if score is None or (isinstance(score, float) and math.isnan(score)):
        return '<span style="opacity:0.5;">–</span>'
    color = score_tier(score)
    return (
        f'<span style="display:inline-block;padding:3px 10px;border-radius:999px;'
        f'font-size:0.72rem;font-weight:700;color:{color};background:{color}1a;'
        f'border:1px solid {color}55;">{score:.1f}/5</span>'
    )
