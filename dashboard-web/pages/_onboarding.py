"""First-run onboarding wizard — full-screen Streamlit UI.

Rendered from ``app.py`` *before* the normal navigation when
``services.onboarding.is_first_run()`` returns True. The wizard takes
over the whole page and calls ``st.stop()`` after rendering so the
sidebar/router never loads in the half-configured state.

After a successful save the wizard sets
``st.session_state.onboarding_complete = True`` and reruns; the parent
gate in ``app.py`` sees the user-layer files now exist and skips
straight to the dashboard.

Re-entrant by design: every input is bound to a session_state key
keyed off the step number, so partial answers survive Streamlit reruns
within a step.
"""

from __future__ import annotations

import io
from dataclasses import asdict
from pathlib import Path

import streamlit as st

from services import onboarding as ob
from services import project_root


TOTAL_STEPS = 8


# ── Session-state plumbing ────────────────────────────────────────────

def _get_state() -> ob.OnboardingState:
    if "onboarding_state" not in st.session_state:
        st.session_state.onboarding_state = ob.OnboardingState(
            timezone="Asia/Singapore",
            company_enabled=ob.default_company_state(),
        )
    return st.session_state.onboarding_state


def _step() -> int:
    return int(st.session_state.get("onboarding_step", 1))


def _set_step(n: int) -> None:
    st.session_state.onboarding_step = max(1, min(TOTAL_STEPS, int(n)))


# ── Chrome ────────────────────────────────────────────────────────────

def _header():
    step = _step()
    progress = (step - 1) / TOTAL_STEPS
    st.markdown(
        f"""
        <div style="
          display:flex;align-items:center;justify-content:space-between;
          margin-bottom:0.6rem;
        ">
          <div style="display:flex;align-items:center;gap:10px;">
            <span style="font-size:1.4rem;">🎯</span>
            <span style="color:var(--tx);font-weight:600;font-size:1.05rem;
                         letter-spacing:-0.01em;">career-ops · setup</span>
          </div>
          <div class="section-label" style="margin-bottom:0;">
            step {step} of {TOTAL_STEPS}
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.progress(progress)


def _nav(*, allow_next: bool = True, next_label: str = "Next →",
         hide_back: bool = False, hide_next: bool = False):
    """Bottom-row Back / Next buttons. Returns nothing; side-effect only."""
    cols = st.columns([1, 1, 6, 1, 1])
    step = _step()

    if not hide_back and step > 1:
        with cols[0]:
            if st.button("← Back", key=f"back_{step}", use_container_width=True):
                _set_step(step - 1)
                st.rerun()

    if not hide_next:
        with cols[-1]:
            if st.button(
                next_label,
                key=f"next_{step}",
                use_container_width=True,
                type="primary",
                disabled=not allow_next,
            ):
                _set_step(step + 1)
                st.rerun()


# ── Steps ─────────────────────────────────────────────────────────────

def _step_1_welcome():
    st.markdown(
        '<div class="hero-card">'
        '<h1>Let\'s set up career-ops</h1>'
        '<div class="hero-sub">'
        "career-ops is an AI job-search pipeline: it tracks every offer, "
        "scores fit against your CV, generates tailored applications, and "
        "scans portals so you don't miss roles. "
        "This short wizard configures your personal layer — the system "
        "files stay untouched, and updates won't overwrite what you enter "
        "here."
        '</div>'
        '</div>',
        unsafe_allow_html=True,
    )

    missing = ob.missing_user_files()
    if missing:
        st.markdown('<div class="section-label">Files we still need</div>',
                    unsafe_allow_html=True)
        st.markdown("\n".join(f"- `{p}`" for p in missing))
    else:
        st.success("Everything's already in place — you can skip the wizard.")

    st.markdown(" ")
    cols = st.columns([1, 1, 6, 1, 2])
    with cols[-1]:
        if st.button("Get started →", type="primary",
                     use_container_width=True, key="welcome_start"):
            _set_step(2)
            st.rerun()


def _step_2_cv():
    state = _get_state()
    st.markdown("### Your CV")
    st.caption(
        "We need this once. The dashboard reads `cv.md` for every "
        "evaluation, so make sure it's clean markdown."
    )

    mode = st.radio(
        "How would you like to provide it?",
        options=["Upload PDF", "Paste markdown", "Start from template"],
        horizontal=True,
        key="cv_mode_radio",
    )

    if mode == "Upload PDF":
        uploaded = st.file_uploader(
            "Drop a PDF here", type=["pdf"], key="cv_pdf_uploader",
        )
        if uploaded is not None and not state.cv_markdown:
            try:
                state.cv_markdown = ob.pdf_to_markdown(io.BytesIO(uploaded.getvalue()))
                st.success(
                    "Converted. Multi-column CVs don't round-trip perfectly — "
                    "review the markdown below and clean up before saving."
                )
            except Exception as e:
                st.error(f"PDF conversion failed: {e}")
                state.cv_markdown = ""

    elif mode == "Start from template":
        if not state.cv_markdown:
            state.cv_markdown = ob.CV_SCRATCH_TEMPLATE

    # Always show an editor — even for PDF / template flows, the user
    # gets to review before save.
    state.cv_markdown = st.text_area(
        "cv.md preview (edit freely)",
        value=state.cv_markdown,
        height=320,
        key="cv_textarea",
        help="Plain markdown. Saved to cv.md on finish.",
    )

    allow_next = bool(state.cv_markdown.strip() and len(state.cv_markdown) > 40)
    if not allow_next:
        st.caption("Add at least a few lines of CV content to continue.")

    _nav(allow_next=allow_next)


def _step_3_profile():
    state = _get_state()
    st.markdown("### Profile basics")
    st.caption("Name and email are required. Everything else is optional.")

    col1, col2 = st.columns(2)
    with col1:
        state.full_name = st.text_input("Full name *", value=state.full_name)
        state.email = st.text_input("Email *", value=state.email)
        state.phone = st.text_input("Phone", value=state.phone)
        state.location = st.text_input(
            "Location", value=state.location,
            placeholder="Singapore, Singapore",
        )
    with col2:
        tz_options = [
            "Asia/Singapore", "Asia/Hong_Kong", "Asia/Tokyo",
            "Asia/Kolkata", "Asia/Dubai",
            "Europe/London", "Europe/Berlin", "Europe/Madrid",
            "America/New_York", "America/Los_Angeles",
            "Australia/Sydney", "Other (set later)",
        ]
        idx = tz_options.index(state.timezone) if state.timezone in tz_options else 0
        state.timezone = st.selectbox("Timezone", tz_options, index=idx)
        state.linkedin = st.text_input(
            "LinkedIn URL", value=state.linkedin,
            placeholder="linkedin.com/in/yourhandle",
        )
        state.portfolio_url = st.text_input(
            "Portfolio URL", value=state.portfolio_url,
        )
        state.github = st.text_input(
            "GitHub", value=state.github,
            placeholder="github.com/yourhandle",
        )

    if not state.visa_status:
        state.visa_status = (
            "Open to roles where employer can sponsor / transfer EP / H1B / etc."
        )
    state.visa_status = st.text_area(
        "Visa / work-authorization status", value=state.visa_status, height=80,
    )

    allow_next = bool(state.full_name.strip()) and "@" in state.email
    if not allow_next:
        st.caption("Name + a valid email are required to continue.")

    _nav(allow_next=allow_next)


def _step_4_roles():
    state = _get_state()
    st.markdown("### Target roles + archetypes")
    st.caption(
        "Pick the role titles to scan for, then tell the system which "
        "archetypes describe you best — primary and secondary are weighted "
        "differently when scoring offers."
    )

    if not state.target_titles:
        # Pre-fill with first 5 defaults so the field isn't empty.
        state.target_titles = ob.DEFAULT_TARGET_TITLES[:5]

    state.target_titles = st.multiselect(
        "Target titles (you can add custom ones below)",
        options=list({*ob.DEFAULT_TARGET_TITLES, *state.target_titles}),
        default=state.target_titles,
        key="target_titles_multi",
    )

    col_a, col_b = st.columns([4, 1])
    with col_a:
        custom_title = st.text_input(
            "Add a custom title", key="custom_title_input",
            placeholder="e.g. Head of Decision Management",
        )
    with col_b:
        st.markdown("&nbsp;", unsafe_allow_html=True)
        if st.button("Add", key="add_custom_title", use_container_width=True):
            t = custom_title.strip()
            if t and t not in state.target_titles:
                state.target_titles.append(t)
                st.rerun()

    st.markdown(
        '<div class="section-label" style="margin-top:1rem;">Archetypes</div>',
        unsafe_allow_html=True,
    )

    for key, title, blurb in ob.DEFAULT_ARCHETYPES:
        c1, c2 = st.columns([3, 2])
        with c1:
            st.markdown(f"**{title}**  \n<span style='color:var(--tx3);font-size:0.82rem;'>{blurb}</span>",
                        unsafe_allow_html=True)
        with c2:
            current = state.archetype_fit.get(key, "secondary")
            choice = st.radio(
                label=title,
                options=["primary", "secondary", "skip"],
                index=["primary", "secondary", "skip"].index(current),
                horizontal=True,
                key=f"arch_{key}",
                label_visibility="collapsed",
            )
            state.archetype_fit[key] = choice

    allow_next = bool(state.target_titles)
    if not allow_next:
        st.caption("Pick at least one target title.")
    _nav(allow_next=allow_next)


def _step_5_comp():
    state = _get_state()
    st.markdown("### Compensation & location")
    st.caption("All numbers stay local — they live in `config/profile.yml`.")

    cur_idx = ob.CURRENCY_OPTIONS.index(state.salary_currency) \
        if state.salary_currency in ob.CURRENCY_OPTIONS else 0
    col1, col2, col3 = st.columns([1, 2, 2])
    with col1:
        state.salary_currency = st.selectbox(
            "Currency", ob.CURRENCY_OPTIONS, index=cur_idx,
        )
    with col2:
        state.salary_minimum = st.number_input(
            "Minimum (walk-away)", min_value=0, step=10_000,
            value=int(state.salary_minimum), key="salary_min_input",
        )
    with col3:
        c_low, c_high = st.columns(2)
        with c_low:
            state.salary_target_low = st.number_input(
                "Target low", min_value=0, step=10_000,
                value=int(state.salary_target_low), key="salary_low_input",
            )
        with c_high:
            state.salary_target_high = st.number_input(
                "Target high", min_value=0, step=10_000,
                value=int(state.salary_target_high), key="salary_high_input",
            )

    state.remote_preference = st.radio(
        "Work mode preference",
        options=ob.REMOTE_OPTIONS,
        index=ob.REMOTE_OPTIONS.index(state.remote_preference)
        if state.remote_preference in ob.REMOTE_OPTIONS else 3,
        horizontal=True,
        key="remote_pref_radio",
    )

    state.regional_preference = st.multiselect(
        "Regions of interest",
        options=ob.REGION_OPTIONS,
        default=state.regional_preference or ["Singapore", "APAC"],
        key="regional_pref_multi",
    )

    state.industries = st.multiselect(
        "Target industries (folds into scanner search queries)",
        options=ob.INDUSTRY_OPTIONS,
        default=state.industries,
        key="industries_multi",
    )

    state.preferences = st.text_area(
        "Deal-breakers / preferences, e.g. no on-site, no startups under 20 people",
        value=state.preferences,
        height=90,
        key="preferences_textarea",
    )

    allow_next = state.salary_target_low > 0 or state.salary_minimum > 0
    if not allow_next:
        st.caption("Set at least one of: target-low or minimum.")
    _nav(allow_next=allow_next)


def _step_6_companies():
    state = _get_state()
    st.markdown("### Companies to track")
    st.caption(
        "These power the daily scanner. Anything ticked here is "
        "checked in `portals.yml`; untick what you don't care about."
    )

    cols = st.columns([1, 1, 6])
    with cols[0]:
        if st.button("Tick all", use_container_width=True, key="tick_all_companies"):
            for n in state.company_enabled:
                state.company_enabled[n] = True
            st.rerun()
    with cols[1]:
        if st.button("Untick all", use_container_width=True, key="untick_all_companies"):
            for n in state.company_enabled:
                state.company_enabled[n] = False
            st.rerun()

    for category, names in ob.DEFAULT_COMPANY_CATEGORIES.items():
        with st.expander(f"{category} ({len(names)})", expanded=False):
            grid = st.columns(2)
            for i, name in enumerate(names):
                with grid[i % 2]:
                    state.company_enabled[name] = st.checkbox(
                        name,
                        value=state.company_enabled.get(name, True),
                        key=f"co_{name}",
                    )

    st.markdown(
        '<div class="section-label" style="margin-top:1rem;">Custom companies</div>',
        unsafe_allow_html=True,
    )
    if state.custom_companies:
        st.write(", ".join(state.custom_companies))

    col_a, col_b = st.columns([4, 1])
    with col_a:
        new_co = st.text_input(
            "Add a company", key="custom_co_input",
            placeholder="e.g. Munich Re",
        )
    with col_b:
        st.markdown("&nbsp;", unsafe_allow_html=True)
        if st.button("Add", key="add_custom_co", use_container_width=True):
            name = new_co.strip()
            if name and name not in state.custom_companies:
                state.custom_companies.append(name)
                st.rerun()

    _nav(allow_next=True)


def _step_7_narrative():
    state = _get_state()
    st.markdown("### Narrative (optional)")
    st.caption(
        "Optional but valuable — the more context you give, the better "
        "the evaluations get. You can skip and add it later in Settings."
    )

    state.superpower = st.text_area(
        "What makes you unique? Your 'superpower'?",
        value=state.superpower, height=110,
        placeholder=("e.g. I run analytics orgs in regulated APAC insurance. "
                     "I ship working AI in 90 days, not 9 months."),
    )
    state.excites_drains = st.text_area(
        "What kind of work excites you? What drains you?",
        value=state.excites_drains, height=110,
    )
    state.dealbreakers = st.text_area(
        "Any deal-breakers? (no on-site, no startups under 20, etc.)",
        value=state.dealbreakers, height=110,
    )

    cols = st.columns([1, 1, 6, 1, 1])
    step = _step()
    with cols[0]:
        if st.button("← Back", key=f"back_{step}", use_container_width=True):
            _set_step(step - 1)
            st.rerun()
    with cols[-2]:
        if st.button("Skip for now", key="skip_narrative",
                     use_container_width=True):
            _set_step(step + 1)
            st.rerun()
    with cols[-1]:
        if st.button("Next →", key=f"next_{step}",
                     use_container_width=True, type="primary"):
            _set_step(step + 1)
            st.rerun()


def _step_8_review():
    state = _get_state()
    st.markdown("### Review and finish")
    st.caption("Double-check, then save. You can edit any of this later "
               "in Settings.")

    with st.container(border=True):
        cols = st.columns(2)
        with cols[0]:
            st.markdown("**Candidate**")
            st.write(f"- {state.full_name or '_(unset)_'}")
            st.write(f"- {state.email or '_(unset)_'}")
            st.write(f"- {state.location or '_(unset)_'} · {state.timezone}")
            st.markdown("**Comp**")
            comp_summary = (
                f"{state.salary_currency} "
                f"{state.salary_target_low:,}–{state.salary_target_high:,} "
                f"(min {state.salary_minimum:,})"
                if state.salary_target_low and state.salary_target_high
                else f"{state.salary_currency} (set in profile.yml)"
            )
            st.write(f"- {comp_summary}")
            st.write(f"- Mode: {state.remote_preference}")
            st.write(f"- Regions: {', '.join(state.regional_preference) or '_(open)_'}")
        with cols[1]:
            st.markdown("**Target titles**")
            for t in state.target_titles or ["_(none)_"]:
                st.write(f"- {t}")
            st.markdown("**Archetypes**")
            for key, title, _ in ob.DEFAULT_ARCHETYPES:
                fit = state.archetype_fit.get(key, "skip")
                if fit != "skip":
                    st.write(f"- {title} ({fit})")

        enabled_count = sum(1 for v in state.company_enabled.values() if v) \
            + len(state.custom_companies)
        st.markdown(f"**Companies tracked:** {enabled_count}")

    st.markdown(" ")
    cols = st.columns([1, 1, 5, 2])
    with cols[0]:
        if st.button("← Back", key=f"back_{_step()}", use_container_width=True):
            _set_step(_step() - 1)
            st.rerun()
    with cols[-1]:
        if st.button("Confirm and save", key="finish_save",
                     use_container_width=True, type="primary"):
            try:
                written = ob.save_all(state)
                st.success(
                    "Saved {n} files. Launching the dashboard…".format(n=len(written))
                )
                with st.expander("Files written", expanded=False):
                    for label, path in written.items():
                        st.code(f"{label}: {path}", language="text")
                st.session_state.onboarding_complete = True
                # One more rerun → app.py's is_first_run() returns False
                # → wizard exits, dashboard loads.
                if st.button("Launch dashboard →", key="launch_dashboard",
                             type="primary", use_container_width=True):
                    st.rerun()
            except Exception as e:
                st.error(f"Save failed: {e}")
                st.exception(e)


# ── Entry point ───────────────────────────────────────────────────────

def render() -> None:
    """Top-level wizard renderer — called from ``app.py``."""
    _header()

    step = _step()
    if step == 1:
        _step_1_welcome()
    elif step == 2:
        _step_2_cv()
    elif step == 3:
        _step_3_profile()
    elif step == 4:
        _step_4_roles()
    elif step == 5:
        _step_5_comp()
    elif step == 6:
        _step_6_companies()
    elif step == 7:
        _step_7_narrative()
    elif step == 8:
        _step_8_review()
    else:
        st.warning(f"Unknown step {step}; resetting.")
        _set_step(1)
        st.rerun()
