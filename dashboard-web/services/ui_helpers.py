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
        return "#6b7280"  # gray
    if score >= 4.5:
        return "#10b981"  # emerald
    if score >= 4.0:
        return "#22d3ee"  # cyan
    if score >= 3.5:
        return "#f59e0b"  # amber
    if score >= 3.0:
        return "#fb923c"  # orange
    return "#ef4444"  # red


# ── Status color tier ─────────────────────────────────────────────────

_STATUS_COLORS = {
    "Pending": ("#94a3b8", "rgba(148,163,184,0.12)"),
    "Watchlist": ("#a78bfa", "rgba(167,139,250,0.12)"),
    "Evaluated": ("#5E6AD2", "rgba(94,106,210,0.15)"),
    "Applied": ("#22d3ee", "rgba(34,211,238,0.12)"),
    "Responded": ("#60a5fa", "rgba(96,165,250,0.12)"),
    "Interview": ("#34d399", "rgba(52,211,153,0.12)"),
    "Offer": ("#10b981", "rgba(16,185,129,0.18)"),
    "Rejected": ("#f87171", "rgba(248,113,113,0.12)"),
    "Discarded": ("#6b7280", "rgba(107,114,128,0.10)"),
    "SKIP": ("#6b7280", "rgba(107,114,128,0.10)"),
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
