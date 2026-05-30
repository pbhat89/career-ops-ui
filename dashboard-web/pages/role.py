"""Role — single-application drill-in.

Layout:
  HERO: company · role · status · score
  LEFT (3 cols): split-report tabs — Overview · JD Match · Comp · Tailor · Interview · Legitimacy · Raw
  RIGHT (1.15 cols): Actions panel — generate · download · status · LaTeX · Apply prompt · Deep / Outreach prompts

All AI-driven "prompts" (Apply, Outreach, Deep, Training) are saved to
output/prompts/{slug}-{kind}.md so the user can run them in Claude Code
or paste them into another tool. They are not auto-evaluated — career-ops
is built around `claude -p` for evaluations only.
"""

from __future__ import annotations

import datetime as dt
import re

try:
    import fitz  # PyMuPDF — optional, only needed for inline PDF preview
except Exception:  # pragma: no cover — degrade gracefully on minimal installs
    fitz = None
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from services import tracker, reports, styling, project_root, single_eval, batch, runner, interest
from services import cv_templates
from services.ui_helpers import (
    safe_str, has_value, status_badge_html, score_badge_html,
    pill_html, verdict_card_html,
)

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

# Query-param navigation: ?num=N
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


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", str(text).lower()).strip("-")


# Legitimacy values are a short tier ("High Confidence", "Proceed with Caution",
# "Suspicious", "Expired", "Insufficient Data") plus optional parenthetical/dash
# qualifiers. Collapse to a one- or two-word badge so it fits the metric box.
_LEGIT_TIERS = {
    "high confidence":      "High",
    "proceed with caution": "Caution",
    "insufficient data":    "Limited",
}


def _legit_tier(text: str) -> str:
    # Strip qualifiers after "(" or "—"/"-", then map known tiers.
    base = re.split(r"\s*[(—-]", str(text).strip(), maxsplit=1)[0].strip()
    return _LEGIT_TIERS.get(base.lower(), base.split()[0] if base else "—")


company_slug = _slug(company)
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
        <div style="margin-top: 0.7rem;">
            {status_badge_html(status)}
            &nbsp;&nbsp;{score_badge_html(score)}
        </div>
    </div>
    ''',
    unsafe_allow_html=True,
)


# ── Two-column layout ─────────────────────────────────────────────────

main, side = st.columns([3, 1.15], gap="large")


# ── Helpers for prompt generation ────────────────────────────────────

def _prompt_dir() -> "Path":
    d = project_root() / "output" / "prompts"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _read_mode_file(filename: str) -> str:
    """Read a modes/*.md file, fallback to empty string."""
    p = project_root() / "modes" / filename
    if p.exists():
        return p.read_text(encoding="utf-8", errors="ignore")
    return ""


def _save_prompt(kind: str, body: str) -> "Path":
    """Save a generated prompt to output/prompts/{slug}-{kind}-{date}.md."""
    today = dt.date.today().isoformat()
    out = _prompt_dir() / f"{company_slug}-{kind}-{today}.md"
    out.write_text(body, encoding="utf-8")
    return out


def _build_prompt(kind: str, instructions: str, extra_context: str = "") -> str:
    """Compose a self-contained prompt the user can paste into Claude Code or
    feed via `claude -p`. Includes role context, JD URL, and the mode body."""
    parts = [
        f"# {kind.title()} prompt for {company} — {role_title}",
        "",
        f"**Company:** {company}",
        f"**Role:** {role_title}",
        f"**JD URL:** {job_url or '(none on this row)'}",
        f"**Tracker row:** #{int(selected_num)}",
        f"**Status:** {status}",
        f"**Score:** {f'{score:.1f}/5' if score is not None else '—'}",
    ]
    if report and (report.archetype or report.legitimacy):
        parts.append(f"**Archetype:** {report.archetype}")
        parts.append(f"**Legitimacy:** {report.legitimacy}")
    parts.extend(["", "---", "", "## Instructions", "", instructions.strip()])
    if extra_context.strip():
        parts.extend(["", "## Context (from career-ops mode)", "", extra_context.strip()])
    return "\n".join(parts)


# ── RIGHT: Actions panel ──────────────────────────────────────────────

with side:
    with st.container(border=True):
        st.markdown('<div class="section-label">Evaluate</div>', unsafe_allow_html=True)

        is_evaluated = report is not None
        missing_artifact = is_evaluated and (not pdf_exists or not cl_exists)
        can_run = has_value(job_url) and not batch_busy

        # ── CV template picker ────────────────────────────────────────
        # Choice is per-role, remembered in session_state so re-evaluating
        # the same row keeps the user's pick. Default = registry default
        # (classic). Picker is disabled while a batch is running so we
        # don't change templates mid-flight on accident.
        tpl_options = cv_templates.list_templates()
        tpl_slugs = [t.slug for t in tpl_options]
        tpl_default_slug = cv_templates.default_slug()
        tpl_session_key = f"cv_template_{selected_num}"
        if tpl_session_key not in st.session_state:
            st.session_state[tpl_session_key] = (
                tpl_default_slug if tpl_default_slug in tpl_slugs else tpl_slugs[0]
            )
        current_slug = st.session_state[tpl_session_key]
        if current_slug not in tpl_slugs:
            current_slug = tpl_slugs[0]
            st.session_state[tpl_session_key] = current_slug
        tpl_choice_slug = st.selectbox(
            "CV template",
            tpl_slugs,
            index=tpl_slugs.index(current_slug),
            key=tpl_session_key,
            format_func=lambda s: next((t.label for t in tpl_options if t.slug == s), s),
            disabled=batch_busy,
            help="Visual style of the generated PDF. All templates use the same placeholders, so swapping doesn't change downstream steps.",
        )
        tpl_match = next((t for t in tpl_options if t.slug == tpl_choice_slug), None)
        if tpl_match and tpl_match.blurb:
            st.caption(tpl_match.blurb)

        # ── Visual preview of the chosen format ───────────────────────
        # Shows the template rendered with bundled EXAMPLE data (Alex Chen),
        # not the user's cv.md — purely so they can compare layouts before
        # committing. No claude run, no PDF: the real CV is built only when
        # they hit Generate below, and only with this one chosen template.
        with st.expander("👁 Preview this format", expanded=True):
            preview_html = cv_templates.render_example_html(tpl_choice_slug)
            if preview_html:
                # The side panel is narrow; zoom the A4 page down so the whole
                # layout is legible as a thumbnail. zoom reflows (unlike
                # transform:scale), so scrollbars stay sane.
                scaled = preview_html.replace(
                    "</head>",
                    "<style>html{zoom:0.42;}body{margin:0;}</style></head>",
                    1,
                )
                components.html(scaled, height=600, scrolling=True)
                st.caption("Example data — your real CV is built on Generate.")
            else:
                st.caption("Preview unavailable for this template.")

        if not is_evaluated:
            if st.button("✨ Generate evaluation", type="primary", use_container_width=True,
                         disabled=not can_run,
                         help="Score + report + tailored PDF + cover letter."):
                try:
                    req = single_eval.SingleEvalRequest(num=int(selected_num), url=job_url,
                                                        company=company, role=role_title,
                                                        template=tpl_choice_slug)
                    proc = single_eval.run_single(req)
                    st.toast(f"Evaluation started (PID {proc.pid}).", icon="🚀")
                except Exception as e:
                    st.error(f"Failed: {e}")
            if not has_value(job_url):
                st.caption("⚠ Add a JD URL to enable evaluation.")
            elif batch_busy:
                st.caption("⚠ Another evaluation is running.")
        elif missing_artifact:
            if st.button("🔁 Regenerate PDF + cover letter", type="primary",
                         use_container_width=True, disabled=not can_run):
                try:
                    req = single_eval.SingleEvalRequest(num=int(selected_num), url=job_url,
                                                        company=company, role=role_title,
                                                        template=tpl_choice_slug)
                    proc = single_eval.run_single(req)
                    st.toast(f"Regeneration started (PID {proc.pid}).", icon="🚀")
                except Exception as e:
                    st.error(f"Failed: {e}")
            missing = [m for m, ok in [("PDF", pdf_exists), ("cover letter", cl_exists)] if not ok]
            st.caption(f"Missing: {', '.join(missing)}.")
        else:
            st.markdown(
                '<div class="banner banner-success">✓ Evaluation complete</div>',
                unsafe_allow_html=True,
            )
            if can_run and st.button("🔁 Re-evaluate", use_container_width=True,
                                       key=f"reeval_{selected_num}",
                                       help="Replace report, PDF, cover letter with a fresh run."):
                try:
                    req = single_eval.SingleEvalRequest(num=int(selected_num), url=job_url,
                                                        company=company, role=role_title,
                                                        template=tpl_choice_slug)
                    proc = single_eval.run_single(req)
                    st.toast(f"Re-evaluation started (PID {proc.pid}).", icon="🚀")
                except Exception as e:
                    st.error(f"Failed: {e}")

        st.divider()

        if has_value(job_url):
            st.link_button("Open JD posting", job_url, use_container_width=True)

        # Interest — Yes / No / blank (saved to data/interest.tsv)
        cur_interest = interest.load_interest().get(int(selected_num), "")
        interest_options = ["", "Yes", "No"]
        new_interest = st.selectbox(
            "Interest",
            interest_options,
            index=interest_options.index(cur_interest) if cur_interest in interest_options else 0,
            key=f"interest_{selected_num}",
            help="Mark whether you want to pursue this role. Hides 'No' rows from Desk.",
        )
        if new_interest != cur_interest:
            try:
                interest.set_interest(int(selected_num), new_interest)
                st.toast(f"Interest: {new_interest or 'cleared'}", icon="📌")
            except Exception as e:
                st.error(str(e))

        idx = tracker.CANONICAL_STATUSES.index(status) if status in tracker.CANONICAL_STATUSES else 0
        new_status = st.selectbox("Change status", tracker.CANONICAL_STATUSES, index=idx,
                                   key=f"status_{selected_num}")
        if new_status != status:
            if st.button(f"Save → {new_status}", use_container_width=True,
                          key=f"status_btn_{selected_num}"):
                try:
                    tracker.update_status(int(selected_num), new_status)
                    st.toast(f"Status: {new_status}", icon="✅")
                    st.cache_data.clear()
                    st.rerun()
                except Exception as e:
                    st.error(str(e))

        if pdf_exists or cl_exists:
            st.divider()
            st.markdown('<div class="section-label">Artifacts</div>', unsafe_allow_html=True)
            if pdf_exists and fitz is not None:
                with st.expander("📄 Preview PDF", expanded=False):
                    doc = None
                    try:
                        doc = fitz.open(str(pdf_path))
                        mat = fitz.Matrix(1.5, 1.5)
                        for page in doc:
                            pix = page.get_pixmap(matrix=mat)
                            st.image(pix.tobytes("png"), use_container_width=True)
                    except Exception:
                        st.caption("Couldn't render inline — use Download.")
                    finally:
                        if doc is not None:
                            doc.close()
            if pdf_exists:
                with pdf_path.open("rb") as f:
                    st.download_button(
                        "Download PDF", f.read(),
                        file_name=pdf_path.name, mime="application/pdf",
                        use_container_width=True, key=f"dl_pdf_{selected_num}",
                    )
            if cl_exists:
                st.download_button(
                    "Download cover letter",
                    cl_path.read_text(encoding="utf-8"),
                    file_name=cl_path.name, mime="text/markdown",
                    use_container_width=True, key=f"dl_cl_{selected_num}",
                )

            # LaTeX export — runs generate-latex.mjs against this report's slug
            if is_evaluated and st.button("Export CV as LaTeX (.tex)", use_container_width=True,
                                            key=f"latex_{selected_num}",
                                            help="Generates an Overleaf-ready .tex via generate-latex.mjs."):
                with st.spinner("Compiling LaTeX…"):
                    r = runner.generate_latex(slug=company_slug)
                if r.ok:
                    st.toast("LaTeX generated — check output/ for the .tex file.", icon="📄")
                else:
                    st.error("LaTeX generation failed.")
                    st.code((r.stdout or r.stderr)[-1500:], language="text")

    # ── Mode-driven prompts (Apply / Outreach / Deep / Interview-prep) ──
    with st.container(border=True):
        st.markdown('<div class="section-label">Generate prompt</div>', unsafe_allow_html=True)
        st.caption("Composes a ready-to-run prompt and saves it to `output/prompts/`. "
                    "Paste into Claude Code or `claude -p`.")

        prompts = [
            ("apply",           "Apply form helper",       "apply.md",        "Help me fill in this company's application form. Pull tailored answers from my CV and the evaluation report."),
            ("contacto",        "LinkedIn outreach",       "contacto.md",     "Find 2-3 LinkedIn contacts at this company who could refer me, and draft a short outreach DM."),
            ("deep",            "Deep company research",   "deep.md",         "Research this company in depth: leadership, recent news, comp benchmarks, Glassdoor/Blind signals, red flags."),
            ("interview-prep",  "Interview prep brief",    "interview-prep.md", "Build a company-specific interview brief: likely interviewers, common questions, STAR stories to use."),
        ]
        for key, label, mode_file, default_inst in prompts:
            if st.button(label, use_container_width=True, key=f"prompt_{key}_{selected_num}"):
                mode_body = _read_mode_file(mode_file)
                body = _build_prompt(key, default_inst, mode_body[:6000])
                out = _save_prompt(key, body)
                st.toast(f"Saved: {out.relative_to(project_root())}", icon="✍")
                st.session_state[f"prompt_show_{key}_{selected_num}"] = body

            # If we just generated, render expander with the body
            shown = st.session_state.get(f"prompt_show_{key}_{selected_num}")
            if shown:
                with st.expander(f"View {label.lower()} prompt", expanded=False):
                    st.code(shown, language="markdown")
                    st.download_button(
                        "Download .md", shown,
                        file_name=f"{company_slug}-{key}.md",
                        mime="text/markdown",
                        key=f"dl_prompt_{key}_{selected_num}",
                        use_container_width=True,
                    )


# ── LEFT: Detail ──────────────────────────────────────────────────────

with main:
    m1, m2, m3 = st.columns(3)
    m1.metric("Score", f"{score:.1f}/5" if score is not None else "—")
    m2.metric("Status", status)
    if report and has_value(report.legitimacy):
        # The metric value box is sized for short text and ellipsizes long
        # strings mid-word ("Proceed with Caution" → "Procee…"). Show the
        # compact tier and keep the full verdict in the tooltip.
        m3.metric("Legitimacy", _legit_tier(report.legitimacy), help=report.legitimacy)
    elif report and has_value(report.archetype):
        m3.metric("Archetype", report.archetype[:22])
    else:
        m3.metric("Date", row["date"].strftime("%Y-%m-%d") if pd.notna(row["date"]) else "—")

    if notes:
        st.markdown(
            f'<div style="color:var(--tx2);font-size:0.9rem;margin-top:0.6rem;font-style:italic;">{notes}</div>',
            unsafe_allow_html=True,
        )

    st.divider()

    if not report:
        st.info(
            "No evaluation report yet. Click **✨ Generate evaluation** on the right to "
            "run the full pipeline — score + report + tailored PDF + cover letter."
        )
        st.stop()

    st.markdown(
        verdict_card_html(score, (report.tldr or "").strip()),
        unsafe_allow_html=True,
    )

    # ── Split tabs — JD vs Evaluation vs Interview vs Legitimacy ──
    tab_overview, tab_jd, tab_comp, tab_tailor, tab_interview, tab_legit, tab_raw = st.tabs([
        "Overview", "JD Match", "Comp & Demand", "Tailoring",
        "Interview", "Legitimacy", "Raw report",
    ])

    # Strip each block's own `## X) Title` heading: the tabs below supply their
    # own English label, and dropping the heading also removes the legacy
    # Spanish titles ("## E) Plan de Personalización") that older batch reports
    # carry — so every tab renders in English under one clean heading.
    block_a = reports.strip_block_heading(reports.extract_block(report_path, "A") or "")
    block_b = reports.strip_block_heading(reports.extract_block(report_path, "B") or "")
    block_c = reports.strip_block_heading(reports.extract_block(report_path, "C") or "")
    block_d = reports.strip_block_heading(reports.extract_block(report_path, "D") or "")
    block_e = reports.strip_block_heading(reports.extract_block(report_path, "E") or "")
    block_f = reports.strip_block_heading(reports.extract_block(report_path, "F") or "")
    block_g = reports.strip_block_heading(reports.extract_block(report_path, "G") or "")
    global_score = reports.extract_global_score(report_path)
    raw_body = reports.report_body(report_path)

    def _render(md: str, fallback: str):
        if md.strip():
            st.markdown(md)
        else:
            st.caption(fallback)

    with tab_overview:
        if has_value(job_url):
            st.markdown(f"**JD URL:** [{job_url}]({job_url})")
        st.caption(f"Report: `{report_path}`")
        st.divider()
        st.markdown("##### A · Role summary")
        _render(block_a, "Block A not found in this report.")
        if global_score:
            st.divider()
            st.markdown("##### Final score & recommendation")
            st.markdown(global_score)

    with tab_jd:
        st.caption("How your CV matches each line of the JD.")
        st.markdown("##### B · CV match")
        _render(block_b, "Block B (CV Match) not found in this report.")

    with tab_comp:
        st.caption("Detected level, sell-up strategy, comp benchmarks, demand signal.")
        if block_c:
            st.markdown("##### C · Level & strategy")
            st.markdown(block_c)
        if block_d:
            if block_c:
                st.divider()
            st.markdown("##### D · Compensation & demand")
            st.markdown(block_d)
        if not (block_c or block_d):
            st.caption("Blocks C/D not found.")

    with tab_tailor:
        st.caption("Specific CV and LinkedIn changes to make before applying.")
        st.markdown("##### E · Tailoring plan")
        _render(block_e, "Block E (Tailoring Plan) not found.")

    with tab_interview:
        ip_dir = project_root() / "interview-prep"
        prep_files = []
        if ip_dir.exists():
            prep_files = list(ip_dir.glob(f"{company_slug}*"))
        if prep_files:
            pick = st.selectbox("Company-specific brief", prep_files, format_func=lambda p: p.name)
            st.markdown(pick.read_text(encoding="utf-8"))
            st.divider()
        if block_f:
            st.markdown("##### F · Interview plan (STAR stories from the report)")
            st.markdown(block_f)
        else:
            st.caption(
                "No Block F in this report. Generate the interview-prep prompt on the right and "
                "run it in Claude Code to create a dedicated brief."
            )

    with tab_legit:
        st.caption("Is the posting real / live? Recruiter, freshness, salary disclosure, etc.")
        st.markdown("##### G · Posting legitimacy")
        _render(block_g, "Block G (Legitimacy) not found.")

    with tab_raw:
        st.caption(f"Full markdown body of `{report_path}`.")
        st.markdown(raw_body)
