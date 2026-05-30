"""career-ops Streamlit dashboard — entry point with top-nav routing."""

from __future__ import annotations

import os
import re

import streamlit as st

from services import tracker, refresh, styling
from services.ui_helpers import kpi_tile_grid

# Mirror desk.py's expiry signals + inactive set so the sidebar "Jobs Found
# (active)" KPI agrees with the worklist's hide-inactive filter.
_EXPIRED_HINTS = re.compile(r"\b(closed|expired|posting expired|withdrawn|filled)\b", re.IGNORECASE)
_INACTIVE_STATUSES = {"Discarded", "SKIP", "Rejected"}

# Industry-match signal — same target list as desk.py's Insurance bucket.
_INDUSTRY_MATCH_RE = re.compile(
    r"\b(insurance|reinsur|insurtech|insuretech|underwriting|claims|actuari)",
    re.IGNORECASE,
)


def _row_is_expired(row) -> bool:
    status = row.get("status")
    if status in _INACTIVE_STATUSES:
        return True
    notes = row.get("notes")
    if isinstance(notes, str) and notes and _EXPIRED_HINTS.search(notes):
        return True
    return False

st.set_page_config(
    page_title="career-ops",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded",
)
styling.inject()

# ── First-run onboarding gate ─────────────────────────────────────────
# If the user-layer files (cv.md / config/profile.yml / modes/_profile.md /
# portals.yml) are missing, take over the page with the setup wizard
# BEFORE the sidebar/router loads. Once the wizard's save_all() runs, the
# files exist and the next rerun falls through to the normal dashboard.
from services import onboarding as _onboarding  # noqa: E402

if _onboarding.is_first_run() and not st.session_state.get("onboarding_complete"):
    import importlib.util as _ilu  # noqa: E402
    from pathlib import Path as _Path  # noqa: E402

    _wizard_path = _Path(__file__).parent / "pages" / "_onboarding.py"
    _spec = _ilu.spec_from_file_location("_career_onboarding_wizard", _wizard_path)
    _wizard = _ilu.module_from_spec(_spec)
    _spec.loader.exec_module(_wizard)  # type: ignore[union-attr]
    _wizard.render()
    st.stop()


# ── Email gate (active only when CAREEROPS_AUTH_EMAIL is set; off for local) ──
_AUTH_EMAIL = (os.environ.get("CAREEROPS_AUTH_EMAIL") or "").strip().lower()
if _AUTH_EMAIL:
    if not st.session_state.get("auth_ok"):
        st.markdown("### career-ops")
        st.caption("Sign in to continue")
        with st.form("auth_form", clear_on_submit=False):
            email_in = st.text_input("Email", placeholder="your@email")
            if st.form_submit_button("Enter", type="primary"):
                if email_in.strip().lower() == _AUTH_EMAIL:
                    st.session_state.auth_ok = True
                    st.rerun()
                else:
                    st.error("Email not recognized.")
        st.stop()


@st.cache_data(ttl=60)
def cached_apps():
    return tracker.load_applications()


def invalidate():
    cached_apps.clear()


if "refresh_done" not in st.session_state:
    st.session_state.refresh_done = False
if "selected_num" not in st.session_state:
    st.session_state.selected_num = None


# ── Sidebar ────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("### 🎯 career-ops")
    df = cached_apps()
    total = len(df)
    if total:
        # Jobs Found (active) — not Discarded/SKIP/Rejected AND not expired.
        _expired_mask = df.apply(_row_is_expired, axis=1)
        jobs_found = int((~_expired_mask).sum())

        # High-fit — score ≥ 4.3 (NaN excluded).
        import pandas as _pd
        _score_num = _pd.to_numeric(df.get("score"), errors="coerce") if "score" in df.columns else _pd.Series(dtype=float)
        high_fit = int((_score_num >= 4.3).sum())

        # Industry match — insurance/reinsurance/insurtech etc. across company+role+notes.
        def _is_industry(row) -> bool:
            blob = " ".join(
                str(row.get(k) or "") for k in ("company", "role", "notes")
            )
            return bool(_INDUSTRY_MATCH_RE.search(blob))
        industry_match = int(df.apply(_is_industry, axis=1).sum())

        st.markdown(
            kpi_tile_grid([
                ("Jobs Found",     jobs_found,     False),
                ("High-fit ≥4.3",  high_fit,       True),
                ("Industry match", industry_match, False),
            ]),
            unsafe_allow_html=True,
        )
    else:
        st.caption("No applications yet.")

    st.divider()

    # The sidebar used to repeat the five command buttons that already live
    # on Desk → Quick actions. That meant two surfaces for the same five
    # dialogs, so we drop it. A short caption points the user at the cards.
    st.markdown(
        '<div style="color:var(--tx3);font-size:0.78rem;line-height:1.55;">'
        'Actions live on <strong>Desk → Quick actions</strong>.<br>'
        'Per-role commands (PDF · Apply · Contacto · Deep · Interview-prep · LaTeX) '
        'are on the <strong>Role</strong> page.<br>'
        'Training / Project evaluations are on <strong>Signals → Lab</strong>.'
        '</div>',
        unsafe_allow_html=True,
    )

    st.divider()

    if refresh.first_launch():
        st.info("First launch — using existing data.")
        if st.button("Mark as seen", use_container_width=True):
            refresh._mark_refresh()
            st.rerun()

    with st.popover("Settings", use_container_width=True):
        from services import runner
        import yaml as _yaml

        st.markdown("##### Profile")
        profile_file = refresh.project_root() / "config" / "profile.yml"
        if profile_file.exists():
            txt = profile_file.read_text(encoding="utf-8")
            new = st.text_area("profile.yml", value=txt, height=220, key="settings_profile", label_visibility="collapsed")
            if new != txt and st.button("Save profile", key="save_profile", type="primary"):
                try:
                    _yaml.safe_load(new)
                    profile_file.write_text(new, encoding="utf-8")
                    st.success("Saved.")
                except _yaml.YAMLError as e:
                    st.error(f"Invalid YAML: {e}")

        st.markdown("##### Portals")
        portals_file = refresh.project_root() / "portals.yml"
        if portals_file.exists():
            txt = portals_file.read_text(encoding="utf-8")
            new = st.text_area("portals.yml", value=txt, height=220, key="settings_portals", label_visibility="collapsed")
            if new != txt and st.button("Save portals", key="save_portals", type="primary"):
                try:
                    _yaml.safe_load(new)
                    portals_file.write_text(new, encoding="utf-8")
                    st.success("Saved.")
                except _yaml.YAMLError as e:
                    st.error(f"Invalid YAML: {e}")

        st.markdown("##### Diagnostics")
        if st.button("Doctor", key="settings_doctor", use_container_width=True):
            r = runner.doctor()
            st.code((r.stdout or r.stderr)[-2000:])
        if st.button("Verify pipeline", key="settings_verify", use_container_width=True):
            r = runner.verify_pipeline()
            st.code((r.stdout or r.stderr)[-2000:])

    if st.button("Refresh data", use_container_width=True):
        plan = refresh.build_plan(force=True)
        with st.status("Refreshing…", expanded=True) as s:
            for step in plan:
                st.write(f"→ {step.name}")
                step.action()
            refresh._mark_refresh()
            s.update(label="Done", state="complete")
        invalidate()
        st.rerun()


# ── Auto-refresh on second+ launch ────────────────────────────────────

if not st.session_state.refresh_done and refresh.should_auto_refresh():
    plan = refresh.build_plan()
    if plan:
        with st.status("Auto-refreshing your data…", expanded=False) as s:
            for step in plan:
                step.action()
            refresh._mark_refresh()
            st.session_state.refresh_done = True
            s.update(label="Auto-refresh done", state="complete")
        invalidate()


# ── Router: 3 destinations, top-positioned, no Material icons ─────────

desk_page = st.Page("pages/desk.py", title="Desk", default=True)
role_page = st.Page("pages/role.py", title="Role")
signals_page = st.Page("pages/signals.py", title="Signals")

pg = st.navigation([desk_page, role_page, signals_page], position="top")
pg.run()
