"""Presentational helpers — color tiers, badges, pills, metric tiles, NaN-safe getters.

The badge / pill / metric helpers are pure HTML strings so they render anywhere
st.markdown() is used. They intentionally don't depend on streamlit-shadcn-ui
iframes (those don't theme with our CSS).
"""

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
        return "#FBBF24"  # amber
    if score >= 3.0:
        return "#FB923C"  # orange
    return "#F87171"      # red


def score_verdict(score: float | None) -> tuple[str, str, str, str]:
    """Return (label, fg, bg, border) for a fit verdict card."""
    if score is None or (isinstance(score, float) and math.isnan(score)):
        return ("— Not scored", "#888", "rgba(136,136,136,0.08)", "rgba(136,136,136,0.30)")
    if score >= 4.5:
        return ("Strong fit — apply", "#44D49A",
                "rgba(68,212,154,0.10)", "rgba(68,212,154,0.35)")
    if score >= 4.0:
        return ("Good fit — likely apply", "#6EE7B7",
                "rgba(110,231,183,0.10)", "rgba(110,231,183,0.30)")
    if score >= 3.5:
        return ("Borderline — review carefully", "#FBBF24",
                "rgba(251,191,36,0.10)", "rgba(251,191,36,0.35)")
    return ("Low fit — recommend skip", "#F87171",
            "rgba(248,113,113,0.10)", "rgba(248,113,113,0.35)")


# ── Status color tier ─────────────────────────────────────────────────

_STATUS_COLORS = {
    "Pending":     ("#858A91", "rgba(133,138,145,0.10)"),
    "Watchlist":   ("#C4B5FD", "rgba(196,181,253,0.12)"),
    "Evaluated":   ("#44D49A", "rgba(68,212,154,0.14)"),
    "In progress": ("#FBBF24", "rgba(251,191,36,0.12)"),
    "Applied":     ("#5B8FE6", "rgba(91,143,230,0.14)"),
    "Responded":   ("#FBBF24", "rgba(251,191,36,0.12)"),
    "Interview":   ("#6EE7B7", "rgba(110,231,183,0.14)"),
    "Offer":       ("#44D49A", "rgba(68,212,154,0.18)"),
    "Rejected":    ("#F87171", "rgba(248,113,113,0.12)"),
    "Discarded":   ("#5F6469", "rgba(95,100,105,0.10)"),
    "SKIP":        ("#5F6469", "rgba(95,100,105,0.10)"),
    "Failed":      ("#F87171", "rgba(248,113,113,0.12)"),
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


# ── Pill (shadcn-style badge) ─────────────────────────────────────────

_PILL_VARIANTS = {
    "default", "accent", "info", "warn", "danger", "success", "violet", "muted",
}


def pill_html(text: str, variant: str = "default", dot: bool = False) -> str:
    """Return shadcn-style pill HTML. Variants: default, accent, info, warn,
    danger, success, violet, muted. dot=True prepends a colored dot."""
    if variant not in _PILL_VARIANTS:
        variant = "default"
    label = safe_str(text, "?")
    dot_html = '<span class="pill-dot"></span>' if dot else ''
    return f'<span class="pill pill-{variant}">{dot_html}{label}</span>'


# ── KPI tile (sidebar / compact metric) ───────────────────────────────

def kpi_tile_html(label: str, value: Any, accent: bool = False) -> str:
    """Render a single sidebar KPI tile.

    Used in app.py sidebar as a tighter alternative to st.metric — fits
    the narrow sidebar width and keeps the chrome quiet."""
    cls = "kpi-tile-value accent" if accent else "kpi-tile-value"
    return (
        f'<div class="kpi-tile">'
        f'<span class="kpi-tile-label">{label}</span>'
        f'<span class="{cls}">{value}</span>'
        f'</div>'
    )


def kpi_tile_grid(items: list[tuple[str, Any, bool]]) -> str:
    """Render a stacked grid of KPI tiles. Each item: (label, value, accent)."""
    inner = "".join(kpi_tile_html(lbl, val, accent=a) for lbl, val, a in items)
    return f'<div class="kpi-tile-grid">{inner}</div>'


# ── Section header (title + optional description + optional badge) ───

def section_header_html(title: str, description: str | None = None,
                         badge: str | None = None) -> str:
    """Render a section header that pairs a tight title with optional sub.

    Pattern lifted from shadcn cards — title in normal weight, description
    in muted, optional accent pill on the right."""
    parts = [f'<span class="sh-title">{safe_str(title)}</span>']
    if description:
        parts.append(f'<span class="sh-desc">{safe_str(description)}</span>')
    if badge:
        parts.append(f'<span class="sh-badge">{safe_str(badge)}</span>')
    return f'<div class="section-header">{"".join(parts)}</div>'


# ── Status-strip (used by Desk batch progress overlay) ────────────────

def status_strip_html(
    label: str,
    headline: str,
    stats: list[tuple[str, Any]],
    progress: float | None = None,
) -> str:
    """Render the batch-progress overlay block.

    progress: 0..1 — when present, renders a filled bar at the bottom.
    stats: list of (label, value) shown right-aligned."""
    right = "".join(
        f'<div class="status-strip-stat">'
        f'<div class="status-strip-stat-label">{safe_str(lbl)}</div>'
        f'<div class="status-strip-stat-value">{val}</div>'
        f'</div>'
        for lbl, val in stats
    )
    bar = ""
    if progress is not None:
        pct = max(0.0, min(1.0, progress))
        bar = (
            f'<div class="status-strip-bar">'
            f'<div class="status-strip-bar-fill" style="width:{pct*100:.1f}%;"></div>'
            f'</div>'
        )
    return (
        f'<div class="status-strip">'
        f'  <div style="width:100%;">'
        f'    <div style="display:flex;justify-content:space-between;align-items:center;">'
        f'      <div class="status-strip-left">'
        f'        <div class="status-strip-label">{safe_str(label)}</div>'
        f'        <div class="status-strip-headline">{safe_str(headline)}</div>'
        f'      </div>'
        f'      <div class="status-strip-stats">{right}</div>'
        f'    </div>'
        f'    {bar}'
        f'  </div>'
        f'</div>'
    )


# ── Verdict card (Role page) ──────────────────────────────────────────

def verdict_card_html(score: float | None, tldr: str) -> str:
    """Render the colored fit-verdict + TL;DR card."""
    label, fg, bg, bd = score_verdict(score)
    score_str = f"{score:.1f}/5" if score is not None else "—"
    body = safe_str(tldr, "No TL;DR captured in report.")
    return (
        f'<div class="verdict-card" style="background:{bg};border-color:{bd};">'
        f'<div class="vc-head" style="color:{fg};">{label} · {score_str}</div>'
        f'<div class="vc-body">{body}</div>'
        f'</div>'
    )
