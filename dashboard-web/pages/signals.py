"""Signals — funnel + score distribution + rejection patterns + scan history.

Vega charts use explicit colors so they render on dark backgrounds.
"""

from __future__ import annotations

import altair as alt
import pandas as pd
import streamlit as st

from services import tracker, runner, styling, project_root

styling.inject()


# ── Back navigation ───────────────────────────────────────────────────

bnc1, _, _ = st.columns([1.4, 4, 1])
if bnc1.button("← Back to Desk", key="signals_back_btn", help="Return to the worklist"):
    st.switch_page("pages/desk.py")


# Dark-mode-safe Vega theme — applied to every chart
def _dark_chart(c: alt.Chart) -> alt.Chart:
    return c.configure_view(
        stroke=None, fill="#101113",
    ).configure_axis(
        labelColor="#B4B8BF", titleColor="#8A8F98",
        gridColor="#1C1D20", domainColor="#26282D",
        tickColor="#26282D", labelFontSize=11, titleFontSize=11,
    ).configure_title(
        color="#F7F8F8", fontSize=13, anchor="start",
    )


st.title("Signals")
st.caption("Where the pipeline leaks, what's working, where new offers come from.")

df = tracker.load_applications()
if df.empty:
    st.info("No applications yet.")
    st.stop()


tab_funnel, tab_patterns, tab_scan = st.tabs(["Funnel", "Patterns", "Scan history"])


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
            .mark_bar(cornerRadius=4, color="#C2522D", fill="#C2522D")
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
                .mark_bar(cornerRadius=4, color="#D26142", fill="#D26142")
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
