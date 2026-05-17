"""Role — single-application drill-in.

Single source of truth for actions:
  * Generate / Re-evaluate   → runs full pipeline (score + report + PDF + cover letter)
  * Download PDF             → only shows if file already exists
  * Download cover letter    → only shows if file already exists
  * Open JD                  → only shows if URL present
  * Status change            → always available

Missing PDF or cover letter never produces a disabled button — instead the user
sees a clear "Generate evaluation" CTA that produces all four artifacts at once.
"""

from __future__ import annotations

import fitz
import pandas as pd
import streamlit as st

from services import tracker, reports, styling, project_root, single_eval, batch
from services.ui_helpers import safe_str, has_value, status_badge_html, score_badge_html

styling.inject()


# ── Back navigation ───────────────────────────────────────────────────

bnc1, _, _ = st.columns([1.4, 4, 1])
if bnc1.button("← Back to Desk", key="role_back_btn", help="Return to the worklist"):
    st.switch_page("pages/desk.py")


# ── Pick the role ─────────────────────────────────────────────────────

df = tracker.load_applications()
if df.empty:
    st.title("Role")
    st.info("No applications yet. Go to **Desk** to scan or evaluate.")
    st.stop()

all_nums = df["num"].tolist()

# Query-param navigation: ?num=N (set by the worklist "Open" LinkColumn) overrides session state.
_qp_num = st.query_params.get("num")
if _qp_num is not None:
    try:
        _qp_int = int(_qp_num)
        if _qp_int in all_nums:
            st.session_state.selected_num = _qp_int
    except (TypeError, ValueError):
        pass

selected_num = st.session_state.get("selected_num")
if selected_num not in all_nums:
    selected_num = all_nums[0]
    st.session_state.selected_num = selected_num

picked = st.selectbox(
    "Role",
    options=all_nums,
    format_func=lambda n: f"#{n} — {df.loc[df['num'] == n, 'company'].iloc[0]}: {safe_str(df.loc[df['num'] == n, 'role'].iloc[0])[:70]}",
    index=all_nums.index(selected_num),
    label_visibility="collapsed",
)
if picked != selected_num:
    st.session_state.selected_num = picked
    selected_num = picked

row = df.loc[df["num"] == selected_num].iloc[0]
company = safe_str(row["company"], "Unknown")
role_title = safe_str(row["role"], "—")
job_url = safe_str(row["job_url"])
notes = safe_str(row["notes"])
score = row["score"] if pd.notna(row["score"]) else None
status = safe_str(row["status"], "Pending")
report_path = safe_str(row["report_path"])
report = reports.parse_report(report_path) if report_path else None

# Resolve PDF + cover letter file paths
pdf_rel = safe_str(report.pdf) if report else ""
cl_rel = safe_str(report.cover_letter) if report else ""
pdf_path = (project_root() / pdf_rel) if pdf_rel else None
cl_path = (project_root() / cl_rel) if cl_rel else None
pdf_exists = bool(pdf_path and pdf_path.exists())
cl_exists = bool(cl_path and cl_path.exists())

batch_busy = single_eval.is_busy()


# ── Hero ───────────────────────────────────────────────────────────────

st.markdown(
    f'''
    <div class="hero-card">
        <h1>{company}</h1>
        <div class="hero-sub">{role_title}</div>
        <div style="margin-top: 0.8rem;">
            {status_badge_html(status)}
            &nbsp;&nbsp;{score_badge_html(score)}
        </div>
    </div>
    ''',
    unsafe_allow_html=True,
)


# ── Two-column layout ─────────────────────────────────────────────────

main, side = st.columns([3, 1.15], gap="large")


# ── RIGHT: Actions panel ──────────────────────────────────────────────

with side:
    with st.container(border=True):
        st.markdown('<div class="section-label">Actions</div>', unsafe_allow_html=True)

        is_evaluated = report is not None
        missing_artifact = is_evaluated and (not pdf_exists or not cl_exists)
        can_run = has_value(job_url) and not batch_busy

        # When the role is FULLY evaluated, lead with the downloads.
        # When NOT evaluated, lead with the big Generate CTA.
        # When evaluated but artifacts missing, lead with Regenerate CTA.

        if not is_evaluated:
            # ── Not yet evaluated → big primary CTA ──
            if st.button("✨ Generate evaluation", type="primary", use_container_width=True,
                         disabled=not can_run,
                         help="Runs the full pipeline: score + report + tailored PDF + cover letter."):
                try:
                    req = single_eval.SingleEvalRequest(num=int(selected_num), url=job_url, company=company, role=role_title)
                    proc = single_eval.run_single(req)
                    st.toast(f"Evaluation started (PID {proc.pid}). Watch the Desk for progress.", icon="🚀")
                except Exception as e:
                    st.error(f"Failed: {e}")
            if not has_value(job_url):
                st.caption("⚠ Add a JD URL on this row to enable evaluation.")
            elif batch_busy:
                st.caption("⚠ Another evaluation is currently running.")

        elif missing_artifact:
            # ── Evaluated but missing PDF/cover letter → prominent regen CTA ──
            if st.button("🔁 Regenerate PDF + cover letter", type="primary", use_container_width=True,
                         disabled=not can_run,
                         help="Re-runs the full evaluation to produce the missing artifacts."):
                try:
                    req = single_eval.SingleEvalRequest(num=int(selected_num), url=job_url, company=company, role=role_title)
                    proc = single_eval.run_single(req)
                    st.toast(f"Regeneration started (PID {proc.pid}).", icon="🚀")
                except Exception as e:
                    st.error(f"Failed: {e}")
            missing = []
            if not pdf_exists: missing.append("PDF")
            if not cl_exists: missing.append("cover letter")
            st.caption(f"Missing: {', '.join(missing)}.")

        else:
            # ── Already evaluated, all artifacts present → quiet refresh option ──
            st.markdown(
                f'<div style="background:rgba(74,222,128,0.08);border:1px solid rgba(74,222,128,0.30);'
                f'border-radius:8px;padding:10px 14px;margin-bottom:10px;color:#86efac;font-size:0.88rem;">'
                f'✓ Evaluation complete</div>',
                unsafe_allow_html=True,
            )

        st.divider()

        # JD link (only if URL present)
        if has_value(job_url):
            st.link_button("Open JD posting", job_url, use_container_width=True)

        # Status changer
        idx = tracker.CANONICAL_STATUSES.index(status) if status in tracker.CANONICAL_STATUSES else 0
        new_status = st.selectbox("Change status", tracker.CANONICAL_STATUSES, index=idx, key=f"status_{selected_num}")
        if new_status != status:
            if st.button(f"Save → {new_status}", use_container_width=True, key=f"status_btn_{selected_num}"):
                try:
                    tracker.update_status(int(selected_num), new_status)
                    st.toast(f"Status: {new_status}", icon="✅")
                    st.cache_data.clear()
                    st.rerun()
                except Exception as e:
                    st.error(str(e))

        # Downloads — only render if file exists (no disabled buttons)
        if pdf_exists or cl_exists:
            st.divider()
            st.markdown('<div class="section-label">Artifacts</div>', unsafe_allow_html=True)
            if pdf_exists:
                # Inline preview via server-side PyMuPDF rendering (Chrome blocks data:application/pdf iframes).
                with st.expander("📄 Preview PDF", expanded=False):
                    doc = None
                    try:
                        doc = fitz.open(str(pdf_path))
                        mat = fitz.Matrix(1.5, 1.5)
                        for page in doc:
                            pix = page.get_pixmap(matrix=mat)
                            st.image(pix.tobytes("png"), use_container_width=True)
                    except Exception:
                        st.caption("Couldn't render inline — use Download below.")
                    finally:
                        if doc is not None:
                            doc.close()
                with pdf_path.open("rb") as f:
                    st.download_button(
                        "Download PDF",
                        f.read(),
                        file_name=pdf_path.name,
                        mime="application/pdf",
                        use_container_width=True,
                        key=f"dl_pdf_{selected_num}",
                    )
            if cl_exists:
                st.download_button(
                    "Download cover letter",
                    cl_path.read_text(encoding="utf-8"),
                    file_name=cl_path.name,
                    mime="text/markdown",
                    use_container_width=True,
                    key=f"dl_cl_{selected_num}",
                )

        # Secondary re-evaluate for already-evaluated rows (small, quiet)
        if is_evaluated and not missing_artifact and can_run:
            st.divider()
            if st.button("🔁 Re-evaluate", use_container_width=True, key=f"reeval_{selected_num}",
                         help="Replaces the current report, PDF and cover letter with a fresh run."):
                try:
                    req = single_eval.SingleEvalRequest(num=int(selected_num), url=job_url, company=company, role=role_title)
                    proc = single_eval.run_single(req)
                    st.toast(f"Re-evaluation started (PID {proc.pid}).", icon="🚀")
                except Exception as e:
                    st.error(f"Failed: {e}")


# ── LEFT: Detail ──────────────────────────────────────────────────────

with main:
    # Metric strip — guaranteed non-empty labels
    m1, m2, m3 = st.columns(3)
    m1.metric("Score", f"{score:.1f}/5" if score is not None else "—")
    m2.metric("Status", status)
    if report and has_value(report.legitimacy):
        m3.metric("Legitimacy", report.legitimacy[:22])
    elif report and has_value(report.archetype):
        m3.metric("Archetype", report.archetype[:22])
    else:
        m3.metric("Date", row["date"].strftime("%Y-%m-%d") if pd.notna(row["date"]) else "—")

    if notes:
        st.markdown(f'<div style="color:var(--tx2);font-size:0.9rem;margin-top:0.6rem;font-style:italic;">{notes}</div>', unsafe_allow_html=True)

    st.divider()

    if not report:
        st.info(
            "No evaluation report yet. Click **✨ Generate evaluation** on the right to "
            "run the full pipeline — score + report + tailored PDF + cover letter."
        )
        st.stop()

    tab_report, tab_jd, tab_interview = st.tabs(["Report", "JD", "Interview prep"])

    with tab_report:
        # ── Fit verdict (2-line summary) ──
        if score is None:
            verdict = "— Not scored yet"
            verdict_color = "#888"
            tint_bg = "rgba(136,136,136,0.08)"
            tint_bd = "rgba(136,136,136,0.30)"
        elif score >= 4.5:
            verdict, verdict_color = "✅ Strong fit — apply", "#4ADE80"
            tint_bg, tint_bd = "rgba(74,222,128,0.10)", "rgba(74,222,128,0.35)"
        elif score >= 4.0:
            verdict, verdict_color = "✅ Good fit — likely apply", "#4ADE80"
            tint_bg, tint_bd = "rgba(74,222,128,0.08)", "rgba(74,222,128,0.30)"
        elif score >= 3.5:
            verdict, verdict_color = "⚠ Borderline — review carefully", "#FBBF24"
            tint_bg, tint_bd = "rgba(251,191,36,0.10)", "rgba(251,191,36,0.35)"
        else:
            verdict, verdict_color = "✗ Low fit — recommend skip", "#F87171"
            tint_bg, tint_bd = "rgba(248,113,113,0.10)", "rgba(248,113,113,0.35)"

        tldr = (report.tldr or "").strip() or "No TL;DR captured in report."
        score_str = f"{score:.1f}/5" if score is not None else "—"
        st.markdown(
            f'<div style="background:{tint_bg};border:1px solid {tint_bd};border-radius:8px;'
            f'padding:12px 16px;margin-bottom:14px;">'
            f'<div style="color:{verdict_color};font-weight:600;font-size:0.95rem;margin-bottom:4px;">'
            f'{verdict} · {score_str}</div>'
            f'<div style="color:var(--tx2);font-size:0.88rem;line-height:1.4;">{tldr}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

        # Artifacts strip
        a1, a2 = st.columns(2)
        a1.markdown(
            f'<div style="background:var(--bg-elev);border:1px solid var(--bd);border-radius:8px;padding:10px 14px;">'
            f'<div style="color:var(--tx3);font-size:11px;text-transform:uppercase;letter-spacing:0.06em;">PDF</div>'
            f'<div style="color:var(--tx);font-weight:500;">'
            f'{"✓ " + pdf_path.name if pdf_exists else "Not generated"}</div></div>',
            unsafe_allow_html=True,
        )
        a2.markdown(
            f'<div style="background:var(--bg-elev);border:1px solid var(--bd);border-radius:8px;padding:10px 14px;">'
            f'<div style="color:var(--tx3);font-size:11px;text-transform:uppercase;letter-spacing:0.06em;">Cover letter</div>'
            f'<div style="color:var(--tx);font-weight:500;">'
            f'{"✓ " + cl_path.name if cl_exists else "Not generated"}</div></div>',
            unsafe_allow_html=True,
        )
        st.markdown("")  # spacer
        body = reports.report_body(report_path)
        st.markdown(body)

    with tab_jd:
        if has_value(job_url):
            st.markdown(f"**URL:** [{job_url}]({job_url})")
        else:
            st.caption("No JD URL on this row.")
        jd_md = reports.extract_jd_section(report_path) if report_path else ""
        if jd_md:
            st.divider()
            st.markdown(jd_md)
            st.caption("Captured during evaluation (Block A + B of the report). Open the URL above for the live posting.")
        elif not has_value(job_url):
            st.info("No JD content yet — generate an evaluation to capture it.")

    with tab_interview:
        ip_dir = project_root() / "interview-prep"
        prep_files = []
        if ip_dir.exists():
            slug_company = safe_str(company).lower().replace(" ", "-").replace("/", "-")
            prep_files = list(ip_dir.glob(f"{slug_company}*"))

        if prep_files:
            pick = st.selectbox("Prep file", prep_files, format_func=lambda p: p.name)
            st.markdown(pick.read_text(encoding="utf-8"))
        else:
            st.markdown(f"**How to prep for this role**")
            st.markdown(
                "1. **Review Block F (STAR stories) of the report below** — it has 6–10 stories "
                "already mapped to JD requirements.\n"
                "2. **Research the company:** recent news, leadership moves, recent hires/exits, "
                "Glassdoor comp band, Blind / Levels.fyi data.\n"
                "3. **Prepare 3 questions to ask the interviewer** — team structure, success metrics "
                "for the role, decision-making cadence.\n"
                "4. **Generate a company-specific intel report:** run `/career-ops interview-prep` "
                "in Claude Code (from the project root) — it produces a dedicated "
                f"`interview-prep/{safe_str(company).lower().replace(' ', '-')}*.md` file with "
                "interviewer backgrounds, likely questions, and red flags."
            )
            block_f = reports.extract_interview_section(report_path) if report_path else ""
            if block_f:
                st.divider()
                st.markdown("##### Block F — Interview Plan (from the evaluation report)")
                st.markdown(block_f)
            else:
                st.caption("No Block F captured in this report yet — re-evaluate the role to generate STAR stories.")
