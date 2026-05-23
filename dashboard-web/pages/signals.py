"""Signals — funnel + score distribution + rejection patterns + scan history.

Vega charts use explicit colors so they render on dark backgrounds.
"""

from __future__ import annotations

import altair as alt
import pandas as pd
import streamlit as st

from services import tracker, runner, styling, project_root
from services.ui_helpers import pill_html

styling.inject()


# ── Back navigation ───────────────────────────────────────────────────

bnc1, _, _ = st.columns([1.4, 4, 1])
if bnc1.button("← Back to Desk", key="signals_back_btn", help="Return to the worklist"):
    st.switch_page("pages/desk.py")


# Dark-mode-safe Vega theme — applied to every chart
def _dark_chart(c: alt.Chart) -> alt.Chart:
    return c.configure_view(
        stroke=None, fill="#1C2025",
    ).configure_axis(
        labelColor="#C9CBCF", titleColor="#8C9196",
        gridColor="rgba(255,255,255,0.04)", domainColor="rgba(255,255,255,0.08)",
        tickColor="rgba(255,255,255,0.08)", labelFontSize=11, titleFontSize=11,
    ).configure_title(
        color="#E7E9EC", fontSize=13, anchor="start",
    )


df = tracker.load_applications()
st.markdown(
    f'<div style="display:flex;align-items:center;gap:10px;margin-top:0.3rem;">'
    f'<h1 style="margin:0;">Signals</h1>'
    f'{pill_html(f"{len(df)} applications", "default", dot=True)}'
    f'</div>',
    unsafe_allow_html=True,
)
st.caption("Where the pipeline leaks, what's working, where new offers come from.")

if df.empty:
    st.info("No applications yet.")
    st.stop()


tab_funnel, tab_patterns, tab_scan, tab_lab = st.tabs([
    "Funnel", "Patterns", "Scan history", "Lab"
])


# ── Funnel + score distribution ────────────────────────────────────────

with tab_funnel:
    c1, c2 = st.columns(2)

    with c1:
        st.markdown('<div class="section-label">Status funnel</div>', unsafe_allow_html=True)
        funnel_order = ["Pending", "Watchlist", "Evaluated", "Applied", "Responded", "Interview", "Offer", "Rejected", "Discarded", "SKIP"]
        counts = df["status"].value_counts().reindex([s for s in funnel_order if s in df["status"].values]).reset_index()
        counts.columns = ["status", "count"]
        chart = (
            alt.Chart(counts)
            .mark_bar(cornerRadius=4, color="#3DB985", fill="#3DB985")
            .encode(
                x=alt.X("count:Q", title=None),
                y=alt.Y("status:N", sort=funnel_order, title=None),
                tooltip=["status", "count"],
            )
            .properties(height=320)
        )
        st.altair_chart(_dark_chart(chart), use_container_width=True)

    with c2:
        st.markdown('<div class="section-label">Score distribution</div>', unsafe_allow_html=True)
        scored = df.dropna(subset=["score"])
        if scored.empty:
            st.caption("No scored applications yet.")
        else:
            hist = (
                alt.Chart(scored)
                .mark_bar(cornerRadius=4, color="#6EE7B7", fill="#6EE7B7")
                .encode(
                    x=alt.X("score:Q", bin=alt.Bin(maxbins=10), title="score"),
                    y=alt.Y("count():Q", title=None),
                )
                .properties(height=320)
            )
            st.altair_chart(_dark_chart(hist), use_container_width=True)

    st.divider()
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Total apps", len(df))
    scored_n = int(df["score"].notna().sum())
    k2.metric("Scored", scored_n)
    if scored_n:
        k3.metric("Avg score", f"{df['score'].mean():.2f}")
        k4.metric("≥ 4.0/5", int((df["score"] >= 4.0).sum()))
    else:
        k3.metric("Avg score", "—")
        k4.metric("≥ 4.0/5", 0)


# ── Rejection patterns ────────────────────────────────────────────────

with tab_patterns:
    st.caption("Reads your reports + tracker, flags dimensions (archetype, seniority, remote) where you keep getting filtered out.")
    if st.button("Run pattern analysis", type="primary"):
        with st.spinner("Running analyze-patterns.mjs…"):
            result = runner.analyze_patterns()
        if not result.ok:
            st.error("Pattern analysis failed.")
            st.code(result.stderr[-1500:] or result.stdout[-1500:])
        else:
            payload = result.json() or {}
            patterns = payload.get("patterns", []) if isinstance(payload, dict) else []
            if not patterns:
                st.success("No problematic patterns detected.")
            else:
                for p in patterns:
                    with st.container(border=True):
                        st.markdown(f"**{p.get('dimension', '?')}** — {p.get('value', '?')}")
                        st.caption(p.get("recommendation", ""))
                        st.caption(f"sample: {p.get('count', 0)} apps · reject rate: {p.get('reject_rate', 0)}")

    st.divider()
    st.markdown('<div class="section-label">Follow-ups due</div>', unsafe_allow_html=True)
    if st.button("Recompute cadence"):
        with st.spinner("Running followup-cadence.mjs…"):
            result = runner.followup_cadence()
        if not result.ok:
            st.error("Cadence script failed.")
            st.code(result.stderr[-1500:] or result.stdout[-1500:])
        else:
            payload = result.json() or {}
            overdue = payload.get("overdue", []) if isinstance(payload, dict) else []
            if not overdue:
                st.success("No follow-ups due.")
            else:
                st.dataframe(pd.DataFrame(overdue), use_container_width=True, hide_index=True)


# ── Scan history ──────────────────────────────────────────────────────

with tab_lab:
    st.caption("Standalone evaluations not tied to a single role. Outputs saved to `output/prompts/`.")
    import datetime as _dt, re as _re
    out_dir = project_root() / "output" / "prompts"
    out_dir.mkdir(parents=True, exist_ok=True)

    def _slug(t: str) -> str:
        return _re.sub(r"[^a-z0-9]+", "-", str(t).lower()).strip("-")

    def _read_mode(fname: str) -> str:
        p = project_root() / "modes" / fname
        return p.read_text(encoding="utf-8", errors="ignore") if p.exists() else ""

    lab1, lab2 = st.columns(2)

    with lab1:
        with st.container(border=True):
            st.markdown("**Training / course / cert**")
            st.caption("Evaluate whether a course is worth the time investment against your goals.")
            t_name = st.text_input("Course or cert name", placeholder="e.g. AWS ML Specialty",
                                    key="lab_training_name")
            t_url = st.text_input("URL (optional)", key="lab_training_url")
            t_cost = st.text_input("Cost / time (optional)", placeholder="e.g. $300, 40h",
                                    key="lab_training_cost")
            if st.button("Generate evaluation prompt", key="lab_training_btn",
                          disabled=not t_name.strip()):
                body = (
                    f"# Training evaluation prompt — {t_name}\n\n"
                    f"**Name:** {t_name}\n"
                    f"**URL:** {t_url or '(none)'}\n"
                    f"**Cost / time:** {t_cost or '(unspecified)'}\n\n"
                    "---\n\n## Instructions\n\n"
                    "Evaluate this course / certification against my target archetypes and "
                    "career goals. Output: fit score (0-5), what it unlocks, opportunity cost, "
                    "verdict (Take / Skip / Take if free).\n\n"
                    "## Context (career-ops mode)\n\n"
                    + _read_mode("training.md")[:6000]
                )
                slug = _slug(t_name)[:50]
                out = out_dir / f"training-{slug}-{_dt.date.today().isoformat()}.md"
                out.write_text(body, encoding="utf-8")
                st.toast(f"Saved {out.relative_to(project_root())}", icon="✍")
                with st.expander("View prompt", expanded=True):
                    st.code(body, language="markdown")

    with lab2:
        with st.container(border=True):
            st.markdown("**Portfolio project**")
            st.caption("Evaluate a side-project idea against your archetypes and proof-point needs.")
            p_name = st.text_input("Project name", placeholder="e.g. AI evaluator for resumes",
                                    key="lab_project_name")
            p_desc = st.text_area("One-line description",
                                   placeholder="What does it do? Who is it for?",
                                   key="lab_project_desc", height=80)
            if st.button("Generate evaluation prompt", key="lab_project_btn",
                          disabled=not p_name.strip()):
                body = (
                    f"# Portfolio project evaluation prompt — {p_name}\n\n"
                    f"**Name:** {p_name}\n"
                    f"**Description:** {p_desc or '(unspecified)'}\n\n"
                    "---\n\n## Instructions\n\n"
                    "Evaluate this project idea against my target archetypes and proof-point gaps. "
                    "Output: fit score (0-5), proof points it unlocks, scope to keep it under 2 weeks, "
                    "verdict (Build now / Park / Skip).\n\n"
                    "## Context (career-ops mode)\n\n"
                    + _read_mode("project.md")[:6000]
                )
                slug = _slug(p_name)[:50]
                out = out_dir / f"project-{slug}-{_dt.date.today().isoformat()}.md"
                out.write_text(body, encoding="utf-8")
                st.toast(f"Saved {out.relative_to(project_root())}", icon="✍")
                with st.expander("View prompt", expanded=True):
                    st.code(body, language="markdown")

    st.divider()
    st.markdown("##### Saved prompts")
    saved = sorted(out_dir.glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True)[:20]
    if not saved:
        st.caption("No prompts saved yet.")
    else:
        for p in saved:
            age_d = (_dt.datetime.now() - _dt.datetime.fromtimestamp(p.stat().st_mtime)).days
            with st.expander(f"{p.name} · {age_d}d ago", expanded=False):
                st.code(p.read_text(encoding="utf-8", errors="ignore"), language="markdown")


with tab_scan:
    history_file = project_root() / "data" / "scan-history.tsv"
    if not history_file.exists():
        st.info("No scan history yet. Run a scan from the Desk.")
    else:
        try:
            scan_df = pd.read_csv(history_file, sep="\t")
            st.caption(f"Last {min(50, len(scan_df))} of {len(scan_df)} scan events.")
            if "status" in scan_df.columns:
                statuses = sorted(scan_df["status"].dropna().unique().tolist())
                picked = st.multiselect("Filter status", statuses, default=statuses)
                scan_df = scan_df[scan_df["status"].isin(picked)]

            st.dataframe(
                scan_df.tail(50)[::-1],
                use_container_width=True,
                hide_index=True,
                height=520,
                column_config={
                    "url": st.column_config.LinkColumn("url", display_text="open"),
                },
            )
        except Exception as e:
            st.error(f"Could not parse scan-history.tsv: {e}")
