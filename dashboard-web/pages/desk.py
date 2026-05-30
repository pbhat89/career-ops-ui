"""Desk — landing page.

Layout:
  1. Hero (greeting + last-scan freshness banner)
  2. Action strip: Scan · Evaluate · Tidy · More
  3. Live batch progress (per-row indicator + global summary)
  4. Worklist table — single-click row selection opens role.py
  5. Below-the-fold signals
"""

from __future__ import annotations

import datetime as dt
import json
import re

import pandas as pd
import streamlit as st

try:
    import yaml  # type: ignore
except Exception:
    yaml = None

try:
    from streamlit_autorefresh import st_autorefresh
except ImportError:
    st_autorefresh = None

from services import tracker, batch, runner, styling, project_root, interest, reports
from services.ui_helpers import safe_str, has_value, pill_html, status_strip_html

styling.inject()


# ── Helpers ────────────────────────────────────────────────────────────

_EXPIRED_HINTS = re.compile(r"\b(closed|expired|posting expired|withdrawn|filled)\b", re.IGNORECASE)
INACTIVE_STATUSES = {"Discarded", "SKIP", "Rejected"}

_API_KEYS = (
    "greenhouse", "ashby", "lever", "workday", "smartrecruiters",
    "mycareersfuture", "mcf", "mcf_search",
)
_API_METHODS = {"greenhouse_api", "ashby_api", "lever_api", "api", "workday_api", "mycareersfuture_api"}
# Provider IDs (entries that set `provider: <id>` directly bypass URL detection).
_API_PROVIDER_IDS = {
    "greenhouse", "ashby", "lever", "workday", "mycareersfuture", "local-parser",
}

LAST_REFRESH_PATH = "data/.last-refresh"


def _count_portal_apis() -> tuple[int, int]:
    path = project_root() / "portals.yml"
    if yaml is None or not path.exists():
        return 0, 0
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception:
        return 0, 0
    companies = data.get("tracked_companies") or []
    if not isinstance(companies, list):
        return 0, 0
    total = with_api = 0
    for c in companies:
        if not isinstance(c, dict) or c.get("enabled") is False:
            continue
        total += 1
        # 1. Explicit provider id (e.g. provider: mycareersfuture)
        if str(c.get("provider") or "").lower() in _API_PROVIDER_IDS:
            with_api += 1
            continue
        # 2. ATS-tagged shortcut fields (greenhouse:, ashby:, lever:, workday:, mcf:, etc.)
        if any(c.get(k) for k in _API_KEYS):
            with_api += 1
            continue
        # 3. Recognised hostnames in careers_url
        url = str(c.get("careers_url") or "").lower()
        if any(host in url for host in (
            "jobs.ashbyhq.com", "jobs.lever.co",
            "job-boards.greenhouse.io", "job-boards.eu.greenhouse.io",
            ".myworkdayjobs.com", "mycareersfuture.gov.sg",
        )):
            with_api += 1
            continue
        # 4. Legacy scan_method tag
        method = str(c.get("scan_method") or "").lower()
        if method in _API_METHODS:
            with_api += 1
    return with_api, total


def _portal_company_names(api_only: bool = True) -> list[str]:
    """Return tracked_companies names from portals.yml — for the scan dialog dropdown.

    api_only=True keeps only entries the zero-token scanner can actually hit
    (Greenhouse / Ashby / Lever endpoints). The remaining ~90% are WebSearch-only
    and listing them here just leads to "0 new offers" surprises.
    """
    path = project_root() / "portals.yml"
    if yaml is None or not path.exists():
        return []
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception:
        return []
    out: list[str] = []
    for c in (data.get("tracked_companies") or []):
        if not isinstance(c, dict) or not c.get("name") or c.get("enabled") is False:
            continue
        if api_only:
            # Same recognition rules as _count_portal_apis: explicit provider id,
            # ATS-tagged shortcut fields, recognised hostnames, or workday/mcf shorthand.
            url = str(c.get("careers_url") or "").lower()
            has_api = (
                str(c.get("provider") or "").lower() in _API_PROVIDER_IDS
                or any(c.get(k) for k in _API_KEYS)
                or any(host in url for host in (
                    "jobs.ashbyhq.com", "jobs.lever.co",
                    "job-boards.greenhouse.io", "job-boards.eu.greenhouse.io",
                    ".myworkdayjobs.com", "mycareersfuture.gov.sg",
                ))
            )
            if not has_api:
                continue
        out.append(str(c["name"]).strip())
    return sorted(out, key=str.lower)


def _is_expired_row(row) -> bool:
    if row.get("status") in INACTIVE_STATUSES:
        return True
    note = safe_str(row.get("notes"))
    if note and _EXPIRED_HINTS.search(note):
        return True
    return False


def _last_scan_info() -> tuple[str, int, str]:
    """(latest first_seen YYYY-MM-DD, new on that date, last-refresh ISO timestamp)."""
    hist = project_root() / "data" / "scan-history.tsv"
    latest = "never"
    new_count = 0
    if hist.exists():
        try:
            # on_bad_lines='skip' tolerates legacy header rows with fewer columns
            # than the new provider-emitted rows (the v1.8.x scanner added a
            # `location` column post-v1.7). Without it pandas raises ParserError
            # and we silently fall back to "never" — which masks the real state.
            sh = pd.read_csv(hist, sep="\t", on_bad_lines="skip")
            if "first_seen" in sh.columns and not sh.empty:
                latest = str(sh["first_seen"].max())
                new_count = int((sh["first_seen"] == latest).sum())
        except Exception:
            pass
    marker = project_root() / LAST_REFRESH_PATH
    last_refresh = ""
    if marker.exists():
        try:
            last_refresh = marker.read_text(encoding="utf-8").strip()[:19]
        except Exception:
            last_refresh = ""
    return latest, new_count, last_refresh


def _scan_age_days() -> float | None:
    """Days since data/.last-refresh — falls back to scan-history mtime."""
    p = project_root() / LAST_REFRESH_PATH
    if not p.exists():
        p = project_root() / "data" / "scan-history.tsv"
        if not p.exists():
            return None
    try:
        age = dt.datetime.now() - dt.datetime.fromtimestamp(p.stat().st_mtime)
        return age.total_seconds() / 86400.0
    except Exception:
        return None


def _greeting() -> str:
    h = dt.datetime.now().hour
    if h < 5:   return "Late night"
    if h < 12:  return "Good morning"
    if h < 18:  return "Good afternoon"
    return "Good evening"


def _first_name() -> str:
    if yaml is None:
        return ""
    path = project_root() / "config" / "profile.yml"
    if not path.exists():
        return ""
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception:
        return ""
    name = (data.get("candidate") or {}).get("name") or data.get("name") or ""
    return str(name).strip().split()[0] if name else ""


# ── Hero ───────────────────────────────────────────────────────────────

df = tracker.load_applications()
last_scan, scan_new, last_refresh = _last_scan_info()
scan_age = _scan_age_days()

n_total = len(df)
pending_with_url = batch.evaluable_pending(df) if not df.empty else df
n_evaluable = len(pending_with_url)
fn = _first_name()
greet = f"{_greeting()}, {fn}" if fn else _greeting()

# Hero — greeting + meta pills line
_meta_pills = "".join([
    pill_html(f"{n_total} tracked", "default", dot=True),
    "&nbsp;",
    pill_html(f"{n_evaluable} ready to evaluate", "accent", dot=True),
    "&nbsp;",
    pill_html(f"scan: {last_scan}" + (f" (+{scan_new})" if scan_new else ""), "info"),
] + ([("&nbsp;" + pill_html(f"refreshed {last_refresh}", "muted"))] if last_refresh else []))

st.markdown(
    f"""
    <div class="hero-card">
        <h1>{greet}</h1>
        <div class="hero-sub" style="display:flex;gap:6px;flex-wrap:wrap;align-items:center;">
            {_meta_pills}
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# Freshness banner — surfaces stale scans without making it noisy.
if scan_age is not None and scan_age > 3:
    days = int(scan_age)
    st.markdown(
        f'<div class="banner banner-warn">'
        f'<strong>Scan is {days} day{"s" if days != 1 else ""} old.</strong> '
        f'Run a fresh scan to catch new postings.'
        f'</div>',
        unsafe_allow_html=True,
    )


# ── Action strip — every /career-ops command as a card ────────────────

# Count pending inbox URLs once for the card headline.
_inbox = tracker.read_pipeline_inbox()
n_inbox = len(_inbox["pending"])
n_expired = int(df.apply(_is_expired_row, axis=1).sum()) if not df.empty else 0

st.markdown('<div class="section-label">Quick actions</div>', unsafe_allow_html=True)

# Row 1 — the three "incoming" actions
r1c1, r1c2, r1c3 = st.columns(3, gap="small")
with r1c1:
    st.markdown(
        '<div class="action-card">'
        '<div class="ac-label">Paste JD</div>'
        '<div class="ac-headline">Add a URL</div>'
        '<div class="ac-sub">Drop a job posting URL here — adds it to the inbox for evaluation.</div>'
        '</div>',
        unsafe_allow_html=True,
    )
    if st.button("Paste JD URL", use_container_width=True, key="bulk_paste_btn", type="primary"):
        st.session_state["show_paste_dialog"] = True
with r1c2:
    st.markdown(
        '<div class="action-card">'
        '<div class="ac-label">Scan</div>'
        '<div class="ac-headline">Fresh portal sweep</div>'
        '<div class="ac-sub">Greenhouse · Ashby · Lever — skips anything already in the tracker.</div>'
        '</div>',
        unsafe_allow_html=True,
    )
    if st.button("Run scan", use_container_width=True, key="bulk_scan_btn", type="primary"):
        st.session_state["show_scan_dialog"] = True
with r1c3:
    st.markdown(
        f'<div class="action-card">'
        f'<div class="ac-label">Inbox</div>'
        f'<div class="ac-headline">{n_inbox} pending URL{"s" if n_inbox != 1 else ""}</div>'
        f'<div class="ac-sub">Process URLs accumulated in <code>data/pipeline.md</code>.</div>'
        f'</div>',
        unsafe_allow_html=True,
    )
    if st.button("Open inbox", use_container_width=True, key="bulk_inbox_btn",
                 disabled=(n_inbox == 0 and not _inbox["processed"])):
        st.session_state["show_inbox_dialog"] = True

# Row 2 — the "outgoing" actions
r2c1, r2c2, r2c3 = st.columns(3, gap="small")
with r2c1:
    st.markdown(
        f'<div class="action-card">'
        f'<div class="ac-label">Evaluate</div>'
        f'<div class="ac-headline">{n_evaluable} pending row{"s" if n_evaluable != 1 else ""}</div>'
        f'<div class="ac-sub">Score · report · tailored PDF · cover letter (parallel workers).</div>'
        f'</div>',
        unsafe_allow_html=True,
    )
    if st.button("Evaluate all pending", use_container_width=True, type="primary",
                 disabled=(n_evaluable == 0), key="bulk_eval_btn"):
        st.session_state["show_eval_dialog"] = True
with r2c2:
    st.markdown(
        f'<div class="action-card">'
        f'<div class="ac-label">Tidy</div>'
        f'<div class="ac-headline">{n_expired} expired</div>'
        f'<div class="ac-sub">Mark closed / withdrawn / filled postings as Discarded.</div>'
        f'</div>',
        unsafe_allow_html=True,
    )
    if st.button("Tidy expired", use_container_width=True, key="bulk_tidy_btn",
                 disabled=(n_expired == 0)):
        moved = 0
        for _, r in df.iterrows():
            if r["status"] == "Pending" and _is_expired_row(r):
                try:
                    tracker.update_status(int(r["num"]), "Discarded")
                    moved += 1
                except Exception:
                    pass
        if moved:
            st.toast(f"Moved {moved} expired Pending → Discarded", icon="🗑️")
            st.cache_data.clear()
            st.rerun()
        else:
            st.toast("Nothing to clean up.", icon="✅")
with r2c3:
    st.markdown(
        '<div class="action-card">'
        '<div class="ac-label">Tools</div>'
        '<div class="ac-headline">Diagnostics</div>'
        '<div class="ac-sub">Liveness · normalize · dedup · pattern analysis · update check.</div>'
        '</div>',
        unsafe_allow_html=True,
    )
    if st.button("Open diagnostics", use_container_width=True, key="bulk_diag_btn"):
        st.session_state["show_diag_dialog"] = True


# ── Dialogs ────────────────────────────────────────────────────────────

@st.dialog("Evaluate pending offers", width="large")
def evaluate_dialog(rows: pd.DataFrame):
    st.write(f"Run **{len(rows)}** evaluation(s) — each produces a score, report, tailored PDF, and cover letter.")
    st.caption("Each evaluation calls `claude -p` (uses Claude Max tokens). Workers run in parallel; UI stays usable.")

    st.dataframe(
        rows[["num", "company", "role", "job_url"]].rename(columns={
            "num": "#", "company": "Company", "role": "Role", "job_url": "URL",
        }),
        hide_index=True,
        use_container_width=True,
        height=220,
        column_config={"URL": st.column_config.LinkColumn("URL", display_text="open")},
    )

    default_parallel = min(3, max(2, len(rows))) if len(rows) > 1 else 1
    parallel = st.slider(
        "Parallel workers", 1, 4, default_parallel,
        help="Default 2-3. Higher = faster but more concurrent token use.",
    )
    dry_run = st.checkbox("Dry run (preview only)", value=False)

    c1, c2 = st.columns(2)
    if c1.button("Cancel", use_container_width=True, key="eval_cancel"):
        st.session_state["show_eval_dialog"] = False
        st.rerun()
    if c2.button("Start batch", type="primary", use_container_width=True, key="eval_start"):
        if not batch.bash_available():
            st.error("`bash` not on PATH. Install Git Bash or WSL.")
            return
        if not batch.claude_cli_available():
            st.error("`claude` CLI not on PATH.")
            return
        batch_rows = batch.rows_from_dataframe(rows)
        batch.write_input_tsv(batch_rows)
        try:
            proc = batch.start_batch(parallel=parallel, dry_run=dry_run)
            st.session_state["show_eval_dialog"] = False
            st.toast(f"Batch started (PID {proc.pid}) with {parallel} worker(s).", icon="🚀")
            st.rerun()
        except Exception as e:
            st.error(f"Failed to start batch: {e}")


@st.dialog("Scan portals")
def scan_dialog():
    api_count, total_count = _count_portal_apis()
    st.markdown(
        f'<div style="color:var(--tx3);font-size:0.85rem;margin-bottom:8px;">'
        f'{api_count} of {total_count} tracked companies have an API endpoint. '
        f'Last scan: <strong>{last_scan}</strong>'
        f'{f" · refreshed {last_refresh}" if last_refresh else ""}.'
        f'</div>',
        unsafe_allow_html=True,
    )

    portal_names = _portal_company_names(api_only=True)
    use_filter = st.checkbox("Restrict to one company", value=False, key="scan_use_filter")
    company = ""
    if use_filter and portal_names:
        st.caption(
            f"Only the **{len(portal_names)} API-backed** companies are listed — "
            f"WebSearch-only entries can't be scanned from here."
        )
        company = st.selectbox(
            "Company",
            options=portal_names, index=0, key="scan_company_pick",
        )
    elif use_filter:
        company = st.text_input("Company name", placeholder="e.g. Anthropic", key="scan_company_text")

    dry_run = st.checkbox("Dry run (preview only — no files written)", value=False, key="scan_dryrun")

    c1, c2 = st.columns(2)
    if c1.button("Cancel", use_container_width=True, key="scan_cancel"):
        st.session_state["show_scan_dialog"] = False
        st.rerun()
    if c2.button("Run scan", type="primary", use_container_width=True, key="scan_run"):
        with st.spinner("Scanning portals…"):
            summary = runner.scan_summary(dry_run=dry_run, company=company.strip() or None)

        if summary.get("ok"):
            n_new = int(summary.get("new_offers") or 0)
            scanned = int(summary.get("companies_scanned") or 0)
            dupes = int(summary.get("duplicates") or 0)
            if n_new > 0:
                st.success(f"Found **{n_new} new offer(s)** across {scanned} companies · {dupes} duplicates skipped.")
                with st.expander("New offers", expanded=True):
                    offers = summary.get("offers") or []
                    if offers:
                        _offers_df = pd.DataFrame(offers)[["company", "title", "location", "url"]]
                        st.dataframe(
                            _offers_df,
                            hide_index=True, use_container_width=True,
                            height=min(700, 38 + 35 * (len(_offers_df) + 1)),
                            column_config={"url": st.column_config.LinkColumn("url", display_text="open")},
                        )
            else:
                hint = (
                    "Enable more API-backed companies in **Settings → Portals**."
                    if api_count == 0 else
                    "Either nothing new was posted, or the title filter excluded everything. "
                    "Loosen `title_filter.positive` to widen the net."
                )
                st.warning(f"0 new offers across {scanned} companies. {hint}")

            # Persist a fresh .last-refresh stamp so the freshness banner clears.
            try:
                marker = project_root() / LAST_REFRESH_PATH
                marker.parent.mkdir(parents=True, exist_ok=True)
                marker.write_text(dt.datetime.now().isoformat(), encoding="utf-8")
            except Exception:
                pass

            errors = summary.get("errors") or []
            if errors:
                with st.expander(f"{len(errors)} API error(s)"):
                    for e in errors:
                        st.text(f"✗ {e.get('company','?')}: {e.get('error','?')}")
        else:
            errors = summary.get("errors") or []
            hint = summary.get("hint")
            if hint == "no-api":
                # Name matched but it's a WebSearch-only entry — that's expected
                # for ~90% of portals.yml. Show as info, not error.
                names = ", ".join(summary.get("matched_names") or [])
                st.info(
                    f"**{names}** has no Greenhouse / Ashby / Lever endpoint, so the zero-token "
                    f"scanner can't reach it. Add an `api:` URL in **Settings → Portals**, or use "
                    f"`/career-ops scan` in Claude Code to do a WebSearch-based scan."
                )
            elif hint == "no-match":
                st.warning(
                    f"No company in portals.yml matches **{summary.get('filter_company','?')}**. "
                    f"Check the spelling — picker below shows all enabled companies."
                )
            else:
                st.error("Scan failed.")
                if errors:
                    for e in errors:
                        st.text(f"✗ {e.get('company','?')}: {e.get('error','?')}")
                else:
                    stderr = summary.get("_raw_stderr") or ""
                    if stderr.strip():
                        st.code(stderr[-1500:], language="text")

        st.cache_data.clear()


@st.dialog("Diagnostics", width="large")
def diagnostics_dialog():
    st.caption("Maintenance scripts — safe by default (dry runs preview). Apply when you're happy.")

    tabs = st.tabs(["Liveness", "Normalize statuses", "Dedup tracker", "Update check", "Verify"])

    with tabs[0]:
        st.write("Check Active applications' JD URLs (caps at 20 per run).")
        if st.button("Run liveness check", key="diag_liveness", type="primary"):
            urls = (
                df[df["status"].isin(["Applied", "Responded", "Interview"]) & df["job_url"].notna()]
                ["job_url"].dropna().unique().tolist()[:20]
            )
            if not urls:
                st.info("No active applications with JD URLs to check.")
            else:
                with st.spinner(f"Checking {len(urls)} URLs…"):
                    r = runner.check_liveness(urls)
                if r.ok:
                    st.success(f"Checked {len(urls)} URLs.")
                else:
                    st.error("Liveness check failed.")
                st.code((r.stdout or r.stderr)[-2000:], language="text")

    with tabs[1]:
        st.write("Normalize the Status column to canonical values (Pending / Evaluated / Applied / …).")
        nd1, nd2 = st.columns(2)
        if nd1.button("Dry run", key="diag_norm_dry"):
            r = runner.normalize_statuses(dry_run=True)
            st.code((r.stdout or r.stderr)[-2000:], language="text")
        if nd2.button("Apply", key="diag_norm_apply", type="primary"):
            r = runner.normalize_statuses(dry_run=False)
            st.code((r.stdout or r.stderr)[-2000:], language="text")
            st.cache_data.clear()

    with tabs[2]:
        st.write("Detect duplicate company+role rows in applications.md and merge them.")
        dd1, dd2 = st.columns(2)
        if dd1.button("Dry run", key="diag_dedup_dry"):
            r = runner.dedup_tracker(dry_run=True)
            st.code((r.stdout or r.stderr)[-2000:], language="text")
        if dd2.button("Apply", key="diag_dedup_apply", type="primary"):
            r = runner.dedup_tracker(dry_run=False)
            st.code((r.stdout or r.stderr)[-2000:], language="text")
            st.cache_data.clear()

    with tabs[3]:
        st.write("Check if a new career-ops version is available on GitHub.")
        uc1, uc2 = st.columns(2)
        if uc1.button("Check for updates", key="diag_update_check"):
            r = runner.update_check()
            data = r.json() or {}
            if data.get("status") == "update-available":
                st.warning(f"Update available: **{data.get('local')} → {data.get('remote')}**")
                st.markdown(data.get("changelog") or "_(no changelog excerpt)_")
            elif data.get("status") == "up-to-date":
                st.success("Already on the latest version.")
            else:
                st.info(f"Status: {data.get('status', 'unknown')}")
            st.code(r.stdout[-1500:], language="text")
        if uc2.button("Apply update", key="diag_update_apply", type="primary"):
            r = runner.update_apply()
            st.code((r.stdout or r.stderr)[-2000:], language="text")
            if r.ok:
                st.success("Update applied. Restart the dashboard to pick up changes.")

    with tabs[4]:
        st.write("Run pipeline-integrity checks: orphan rows, malformed entries, missing reports.")
        v1, v2 = st.columns(2)
        if v1.button("Verify pipeline", key="diag_verify", type="primary"):
            r = runner.verify_pipeline()
            st.code((r.stdout or r.stderr)[-2500:], language="text")
        if v2.button("Doctor", key="diag_doctor"):
            r = runner.doctor()
            st.code((r.stdout or r.stderr)[-2500:], language="text")


@st.dialog("Paste a JD URL")
def paste_dialog():
    st.caption(
        "Adds the URL to `data/pipeline.md` (the second-brain inbox). "
        "Run **Inbox → Promote** to bring it into the tracker, or use Claude Code's "
        "`/career-ops {url}` for the full auto-pipeline."
    )
    url = st.text_input("Job posting URL", placeholder="https://boards.greenhouse.io/...",
                         key="paste_url")
    c_col, r_col = st.columns(2)
    company_in = c_col.text_input("Company (optional)", key="paste_company")
    role_in = r_col.text_input("Role (optional)", key="paste_role")

    a, b = st.columns(2)
    if a.button("Cancel", use_container_width=True, key="paste_cancel"):
        st.session_state["show_paste_dialog"] = False
        st.rerun()
    if b.button("Add to inbox", type="primary", use_container_width=True, key="paste_save"):
        try:
            p = tracker.append_to_pipeline(url, company_in, role_in)
            st.toast(f"Added to {p.relative_to(project_root())}", icon="📥")
            st.session_state["show_paste_dialog"] = False
            st.cache_data.clear()
            st.rerun()
        except ValueError as e:
            st.error(str(e))
        except Exception as e:
            st.error(f"Failed to write pipeline.md: {e}")


@st.dialog("Pipeline inbox", width="large")
def inbox_dialog():
    """Show contents of data/pipeline.md — pending and processed sections."""
    data = tracker.read_pipeline_inbox()
    pending = data["pending"]
    processed = data["processed"]

    st.caption(
        f"`data/pipeline.md` · **{len(pending)}** pending · "
        f"**{len(processed)}** processed. "
        f"To turn pending URLs into evaluations, paste a URL into Claude Code via "
        f"`/career-ops {{url}}` (full auto-pipeline) or `/career-ops pipeline` (batch the lot)."
    )

    if pending:
        st.markdown("##### Pending")
        for entry in pending:
            with st.container(border=True):
                pc1, pc2 = st.columns([5, 1])
                with pc1:
                    label = f"[{entry['url']}]({entry['url']})"
                    meta = " · ".join(filter(None, [entry["company"], entry["role"]]))
                    st.markdown(f"{label}" + (f"  \n*{meta}*" if meta else ""))
                with pc2:
                    if st.button("Mark done", key=f"inbox_done_{entry['url']}",
                                  use_container_width=True):
                        if tracker.mark_pipeline_processed(entry["url"]):
                            st.toast("Moved to Processed", icon="✓")
                            st.rerun()
    else:
        st.caption("No pending URLs in the inbox.")

    if processed:
        with st.expander(f"Processed ({len(processed)})", expanded=False):
            for entry in processed:
                meta = " · ".join(filter(None, [entry["company"], entry["role"]]))
                st.markdown(f"- ✓ [{entry['url']}]({entry['url']})" + (f" — *{meta}*" if meta else ""))


# Streamlit only allows ONE dialog open per script run. Pick the first
# active flag and consume EVERY flag (including the active one) before
# rendering — so closing the dialog via the X button can't leave a stuck
# flag that hijacks the next click on a different action.
_DIALOG_KEYS = (
    "show_paste_dialog", "show_scan_dialog", "show_inbox_dialog",
    "show_eval_dialog", "show_diag_dialog", "show_compare_dialog",
)
_active = next((k for k in _DIALOG_KEYS if st.session_state.get(k)), None)
for _k in _DIALOG_KEYS:
    st.session_state[_k] = False

if _active == "show_paste_dialog":
    paste_dialog()
elif _active == "show_scan_dialog":
    scan_dialog()
elif _active == "show_inbox_dialog":
    inbox_dialog()
elif _active == "show_eval_dialog" and not df.empty:
    evaluate_dialog(pending_with_url)
elif _active == "show_diag_dialog":
    diagnostics_dialog()


# ── Auto-merge + Batch progress overlay ────────────────────────────────

_merged_count = batch.auto_merge_if_pending()
if _merged_count > 0:
    st.cache_data.clear()
    df = tracker.load_applications()

state_df = batch.read_state()
summary = batch.state_summary() if not state_df.empty else {"active": False, "total": 0,
                                                              "completed": 0, "failed": 0,
                                                              "in_progress": 0, "pending": 0}

if not state_df.empty:
    if summary["active"] and st_autorefresh is not None:
        st_autorefresh(interval=2000, limit=900, key="batch_autorefresh")

    total = summary["total"] or 1
    done = summary["completed"] + summary["failed"]
    pct = done / total if total else 0
    status_word = "Running…" if summary["active"] else "Done"

    st.markdown(
        status_strip_html(
            label="Batch evaluation",
            headline=f'{done}/{summary["total"]} — {int(pct*100)}% · {status_word}',
            stats=[
                ("In flight", summary["in_progress"]),
                ("Failed", summary["failed"]),
            ],
            progress=pct,
        ),
        unsafe_allow_html=True,
    )

    log_name, log_tail = batch.latest_log_tail(n_lines=10)
    if log_tail:
        with st.expander(f"Live log — {log_name}", expanded=False):
            st.code(log_tail, language="text")

    if not summary["active"]:
        if st.button("Clear batch state", key="clear_batch_state",
                     help="Removes batch-input.tsv and batch-state.tsv so this strip disappears."):
            (project_root() / "batch" / "batch-state.tsv").unlink(missing_ok=True)
            (project_root() / "batch" / "batch-input.tsv").unlink(missing_ok=True)
            st.toast("Batch state cleared.", icon="🧹")
            st.rerun()


# ── Worklist ───────────────────────────────────────────────────────────

if df.empty:
    st.info("No applications yet. Run a scan, or paste a JD URL into pipeline.md.")
    st.stop()

# Build per-row progress overlay from batch-state.tsv
_inprog_ids: set[int] = set()
_failed_ids: set[int] = set()
_completed_ids: set[int] = set()
if not state_df.empty and "id" in state_df.columns:
    for _, br in state_df.iterrows():
        try:
            rid = int(br["id"])
        except (TypeError, ValueError):
            continue
        bs = str(br.get("status", "")).lower()
        if bs in ("processing", "in_progress"):
            _inprog_ids.add(rid)
        elif bs == "failed":
            _failed_ids.add(rid)
        elif bs == "completed":
            _completed_ids.add(rid)

# ── Filter strip ───────────────────────────────────────────────────────

f1, f2, f3, f4 = st.columns([2.2, 1.4, 1.2, 1.0])
f1.markdown("##### Worklist")
sort_choice = f2.selectbox(
    "Sort",
    ["Smart", "Score ↓", "Score ↑", "Date (newest)", "Status"],
    label_visibility="collapsed",
    key="worklist_sort",
)
hide_no = f3.toggle("Hide 'No'", value=True, help="Hide rows you've marked Interest = No.")
show_inactive = f4.toggle("Show inactive", value=False,
                          help="Include Discarded / SKIP / Rejected / expired postings.")

_interest_map = interest.load_interest()

status_order = {
    "Pending": 0, "Watchlist": 1, "Evaluated": 2, "Applied": 3,
    "Responded": 4, "Interview": 5, "Offer": 6, "Rejected": 7,
    "Discarded": 8, "SKIP": 9,
}
df = df.copy()
df["__sort"] = df["status"].map(status_order).fillna(99)
df["__expired"] = df.apply(_is_expired_row, axis=1)
df["__interest"] = df["num"].map(_interest_map).fillna("")

worklist = df if show_inactive else df[~df["__expired"]]
if hide_no:
    worklist = worklist[worklist["__interest"] != "No"]

# Column filters
_status_options = ["Pending", "Watchlist", "Evaluated", "In progress", "Applied",
                    "Responded", "Interview", "Offer", "Rejected", "Discarded", "SKIP"]
_dates = pd.to_datetime(worklist["date"], errors="coerce").dropna()
_date_max = _dates.max().date() if not _dates.empty else dt.date.today()
_date_min = _dates.min().date() if not _dates.empty else _date_max

fc1, fc2, fc3, fc4 = st.columns([1.4, 1.4, 1.6, 1.6])
filter_status = fc1.multiselect("Status", options=_status_options,
                                 default=st.session_state.get("filter_status", []),
                                 key="filter_status", placeholder="Any status")
_company_options = sorted(
    {str(c) for c in worklist["company"].dropna().astype(str) if str(c).strip()}
)
filter_company = fc2.multiselect("Company", options=_company_options,
                                  default=st.session_state.get("filter_company", []),
                                  key="filter_company", placeholder="Any company")
filter_score = fc3.slider("Score range", 0.0, 5.0,
                          value=st.session_state.get("filter_score", (0.0, 5.0)),
                          step=0.1, key="filter_score")
filter_score_unscored = fc3.checkbox("Include unscored",
                                      value=st.session_state.get("filter_score_unscored", True),
                                      key="filter_score_unscored")
filter_date = fc4.date_input("Date range",
                              value=st.session_state.get("filter_date", (_date_min, _date_max)),
                              min_value=_date_min, max_value=_date_max, key="filter_date")

if filter_status:
    _statuses_set = set(filter_status)
    _wanted_in_progress = "In progress" in _statuses_set
    _other_statuses = _statuses_set - {"In progress"}
    mask = worklist["status"].isin(_other_statuses)
    if _wanted_in_progress and _inprog_ids:
        mask = mask | worklist["num"].isin(_inprog_ids)
    worklist = worklist[mask]

if filter_company:
    worklist = worklist[worklist["company"].astype(str).isin(filter_company)]

_lo, _hi = filter_score
if not (_lo == 0.0 and _hi == 5.0 and filter_score_unscored):
    _score_num = pd.to_numeric(worklist["score"], errors="coerce")
    score_mask = (_score_num >= _lo) & (_score_num <= _hi)
    if filter_score_unscored:
        score_mask = score_mask | _score_num.isna()
    worklist = worklist[score_mask]

if isinstance(filter_date, tuple) and len(filter_date) == 2:
    _df_lo, _df_hi = filter_date
    if not (_df_lo == _date_min and _df_hi == _date_max):
        _wd = pd.to_datetime(worklist["date"], errors="coerce")
        worklist = worklist[(_wd.dt.date >= _df_lo) & (_wd.dt.date <= _df_hi)]

# Sort
if sort_choice == "Score ↓":
    worklist = worklist.sort_values(["score", "date"], ascending=[False, False], na_position="last")
elif sort_choice == "Score ↑":
    worklist = worklist.sort_values(["score", "date"], ascending=[True, False], na_position="last")
elif sort_choice == "Date (newest)":
    worklist = worklist.sort_values("date", ascending=False, na_position="last")
elif sort_choice == "Status":
    worklist = worklist.sort_values(["__sort", "date"], ascending=[True, False])
else:
    def _smart_group(s: str) -> int:
        if s == "Evaluated": return 0
        if s in ("Applied", "Responded", "Interview", "Offer"): return 1
        if s == "Watchlist": return 2
        return 3
    worklist = worklist.copy()
    worklist["__group"] = worklist["status"].map(_smart_group).fillna(3).astype(int)
    # In-progress rows should bubble to the top so progress is visible.
    worklist["__active"] = worklist["num"].isin(_inprog_ids)
    worklist = worklist.sort_values(
        ["__active", "__group", "score", "__sort", "date"],
        ascending=[False, True, False, True, False],
        na_position="last",
    )
    worklist = worklist.drop(columns=["__group", "__active"])

worklist = worklist.drop(columns=["__sort", "__expired"])

worklist_view = worklist[["num", "company", "role", "score", "status", "has_pdf",
                          "job_url", "date", "report_path", "__interest"]].copy()
worklist_view["added_date"] = worklist_view["date"].dt.strftime("%Y-%m-%d")
worklist_view["job_url"] = worklist_view["job_url"].fillna("").replace("", None)

# Resolve posted_date + salary from each row's report
_posted_map: dict[int, str] = {}
_salary_map: dict[int, str] = {}
for _, _r in worklist_view.iterrows():
    rp = safe_str(_r.get("report_path"))
    if not rp:
        continue
    try:
        rs = reports.parse_report(rp)
    except Exception:
        rs = None
    if rs is None:
        continue
    try:
        n_ = int(_r["num"])
    except (TypeError, ValueError):
        continue
    if rs.posted_date:
        _posted_map[n_] = rs.posted_date
    if rs.salary_raw:
        _salary_map[n_] = rs.salary_raw


def _date_cell(row) -> str:
    try:
        n_ = int(row["num"])
    except (TypeError, ValueError):
        return row.get("added_date") or ""
    p = _posted_map.get(n_)
    if p:
        return p
    added = row.get("added_date") or ""
    return f"{added} (added)" if added else ""


worklist_view["date"] = worklist_view.apply(_date_cell, axis=1)
worklist_view["salary"] = worklist_view["num"].map(_salary_map).fillna("")
worklist_view = worklist_view.drop(columns=["report_path", "added_date"])
worklist_view = worklist_view.rename(columns={"__interest": "Interest"})


# Build the "Progress" cell — an inline indicator for rows actively in the batch.
def _progress_cell(num: int, status: str) -> str:
    if num in _inprog_ids:
        return "● running"
    if num in _failed_ids and status == "Pending":
        return "✗ failed"
    return ""


worklist_view["Progress"] = worklist_view.apply(
    lambda r: _progress_cell(int(r["num"]), str(r["status"])),
    axis=1,
)


# Overlay batch state on status column
def _overlay_status(r) -> str:
    n_ = int(r["num"])
    if n_ in _inprog_ids:
        return "In progress"
    if n_ in _failed_ids and r["status"] == "Pending":
        return "Failed"
    if n_ in _completed_ids and r["status"] == "Pending":
        # Only show "Evaluated" if a score actually landed
        sc = r.get("score")
        if sc is not None and not (isinstance(sc, float) and pd.isna(sc)):
            return "Evaluated"
    return r["status"]


worklist_view["status"] = worklist_view.apply(_overlay_status, axis=1)

# Per-row Open link: hits the role page directly with ?num=N.
# Streamlit routes pages registered in st.navigation() at /{page_basename},
# so /role?num=42 loads role.py and the existing query-param handler picks
# up the selection.
worklist_view["open"] = worklist_view["num"].apply(lambda n: f"/role?num={int(n)}")

worklist_view = worklist_view.rename(columns={
    "num": "#", "company": "Company", "role": "Role", "score": "Score",
    "status": "Status", "has_pdf": "PDF", "job_url": "JD link", "date": "Date",
    "salary": "Salary", "open": "Review",
})

worklist_view = worklist_view[[
    "#", "Review", "Company", "Role", "Progress", "Score", "Salary",
    "Status", "PDF", "JD link", "Date", "Interest",
]]

# ── Single-click row navigation (smooth Review/Open) ──────────────────
# Streamlit's data_editor supports selection events. We use it so a single
# click anywhere in the row opens role.py — no more two-step "tick then click".

# Auto-expand the worklist to fit up to ~50 rows; clamp so it never exceeds
# typical laptop viewport. Streamlit row ≈ 35 px, header ≈ 38 px.
_row_h = 35
_min_height = 460
_max_height = 1800
_dynamic_height = min(_max_height, max(_min_height, 38 + _row_h * (len(worklist_view) + 1)))

event = st.dataframe(
    worklist_view,
    use_container_width=True,
    hide_index=True,
    height=_dynamic_height,
    key="worklist_table",
    on_select="rerun",
    selection_mode="multi-row",
    column_config={
        "Review": st.column_config.LinkColumn(
            "Review", display_text="open →", width="small",
            help="Click to drill into the role's full evaluation.",
        ),
        "JD link": st.column_config.LinkColumn("JD link", display_text="JD ↗", width="small"),
        "Score": st.column_config.NumberColumn("Score", format="%.1f / 5",
                                                help="— = not evaluated yet"),
        "Salary": st.column_config.TextColumn(
            "Salary", width="small",
            help="Estimated comp band from the evaluation report. Blank = not in JD.",
        ),
        "Progress": st.column_config.TextColumn(
            "Progress", width="small",
            help="Live status: '● running' = evaluation in flight, '✗ failed' = needs retry.",
        ),
        "Date": st.column_config.TextColumn(
            "Date", width="small",
            help="JD posting date when known; tracker add-date otherwise.",
        ),
        "PDF": st.column_config.CheckboxColumn("PDF", width="small"),
    },
)

picked_nums: list[int] = []
if event and getattr(event, "selection", None):
    rows = event.selection.get("rows") or []
    for ri in rows:
        try:
            picked_nums.append(int(worklist_view.iloc[ri]["#"]))
        except (IndexError, KeyError, ValueError):
            pass

st.caption(
    "Click **open →** in any row to drill in. Tick the row checkboxes to compare or batch-evaluate."
)

# ── Bulk action bar (only when 2+ rows selected) ──────────────────────

if picked_nums:
    picked_full = worklist[worklist["num"].isin(picked_nums)].copy()
    all_have_url = bool(len(picked_full)) and picked_full["job_url"].fillna("").astype(str).str.strip().ne("").all()

    _ids_preview = ", ".join(f"#{n}" for n in picked_nums[:6]) + (" …" if len(picked_nums) > 6 else "")
    st.markdown(
        f'<div style="display:flex;gap:8px;align-items:center;margin:12px 0 8px;">'
        f'{pill_html(f"{len(picked_nums)} selected", "accent", dot=True)}'
        f'<span style="color:var(--tx3);font-size:0.82rem;">{_ids_preview}</span>'
        f'</div>',
        unsafe_allow_html=True,
    )
    ab1, ab2, ab3, _ = st.columns([1.7, 1.5, 1.5, 4.3])

    if ab1.button(f"Evaluate {len(picked_nums)}", type="primary", use_container_width=True,
                   disabled=not all_have_url,
                   help=None if all_have_url else "Every selected row needs a JD URL.",
                   key="action_eval"):
        evaluate_dialog(picked_full)

    if ab2.button("Compare", use_container_width=True, key="action_compare",
                   disabled=len(picked_nums) < 2,
                   help="Side-by-side TL;DRs of 2+ scored offers."):
        st.session_state["compare_nums"] = picked_nums
        st.session_state["show_compare_dialog"] = True

    if ab3.button("→ Discarded", use_container_width=True, key="action_discard"):
        moved = 0
        for n in picked_nums:
            try:
                tracker.update_status(int(n), "Discarded")
                moved += 1
            except Exception:
                pass
        if moved:
            st.toast(f"Marked {moved} row(s) as Discarded", icon="🗑️")
            st.cache_data.clear()
            st.rerun()


# ── Compare dialog (ofertas mode) ─────────────────────────────────────

@st.dialog("Compare offers", width="large")
def compare_dialog(nums: list[int]):
    rows = df[df["num"].isin(nums)].copy()
    if rows.empty:
        st.info("No rows.")
        return
    grid = rows[["num", "company", "role", "score", "status", "job_url"]].copy()
    grid["report"] = rows["report_path"]
    grid["salary"] = grid["num"].map(_salary_map).fillna("")
    grid["posted"] = grid["num"].map(_posted_map).fillna("")
    st.dataframe(
        grid.rename(columns={
            "num": "#", "company": "Company", "role": "Role", "score": "Score",
            "status": "Status", "job_url": "URL", "report": "Report", "salary": "Salary",
            "posted": "Posted",
        }),
        hide_index=True, use_container_width=True,
        column_config={"URL": st.column_config.LinkColumn("URL", display_text="open")},
    )
    st.divider()
    st.caption("TL;DR from each evaluation report (Block A):")
    for _, r in rows.iterrows():
        rp = safe_str(r.get("report_path"))
        if not rp:
            continue
        rs = reports.parse_report(rp)
        if rs is None:
            continue
        with st.container(border=True):
            st.markdown(f"**#{int(r['num'])} · {r['company']} — {r['role']}**")
            tldr = (rs.tldr or "_(no TL;DR)_").strip()
            st.markdown(tldr)


if _active == "show_compare_dialog":
    nums = st.session_state.get("compare_nums") or []
    compare_dialog(nums)


# ── Below-the-fold ─────────────────────────────────────────────────────

_INDUSTRY_RULES = [
    ("Insurance / Reinsurance", re.compile(r"\b(insurance|reinsur|insurtech|insuretech|underwriting|claims|actuari)", re.IGNORECASE)),
    ("Banking",                  re.compile(r"\b(bank(?:ing)?|wealth|private bank|capital markets)\b", re.IGNORECASE)),
    ("Consulting",               re.compile(r"\b(consulting|mckinsey|kearney|accenture|capgemini)\b", re.IGNORECASE)),
    ("Tech / SaaS",              re.compile(r"\b(stripe|anthropic|openai|databricks|palantir)\b", re.IGNORECASE)),
    ("Government / Public",      re.compile(r"\b(gov|MAS|ministry|agency)\b", re.IGNORECASE)),
]


def _classify_industry(row) -> str:
    blob = " ".join(safe_str(row.get(k)) for k in ("company", "role", "notes"))
    for name, pat in _INDUSTRY_RULES:
        if pat.search(blob):
            return name
    return "Other / Unsure"


st.markdown("##### Today's signals")
b1, b2, b3 = st.columns(3, gap="medium")

with b1:
    with st.container(border=True):
        st.markdown("**Follow-ups due**")
        st.caption("Applied or Responded > 7 days ago.")
        applied_old = worklist[
            (worklist["status"].isin(["Applied", "Responded"])) &
            (worklist["date"].notna()) &
            ((dt.datetime.now() - worklist["date"]).dt.days >= 7)
        ].head(5)
        if applied_old.empty:
            st.caption("Nothing overdue.")
        else:
            for _, r in applied_old.iterrows():
                age = (dt.datetime.now() - r["date"]).days
                st.write(f"• **{safe_str(r['company'])}** — {age}d since {safe_str(r['status']).lower()}")

with b2:
    with st.container(border=True):
        st.markdown("**Recent reports**")
        recent = worklist[worklist["report_path"] != ""].head(5)
        if recent.empty:
            st.caption("No reports yet.")
        else:
            for _, r in recent.iterrows():
                sc = f"{r['score']:.1f}" if pd.notna(r['score']) else "–"
                st.write(f"• **{safe_str(r['company'])}** · {sc}/5 · {safe_str(r['role'])[:48]}")

with b3:
    with st.container(border=True):
        st.markdown("**Industry mix**")
        st.caption("Bars sized by application count.")
        ind_series = worklist.apply(_classify_industry, axis=1) if not worklist.empty else pd.Series(dtype=str)
        if ind_series.empty:
            st.caption("No rows to classify.")
        else:
            counts = ind_series.value_counts()
            chart_df = counts.rename_axis("Industry").reset_index(name="Count")
            # Horizontal so long category labels (e.g. "Insurance / Reinsurance",
            # "Government / Public") stay readable instead of getting rotated 90°.
            # Green (#3DB985) to match the Signals funnel — st.bar_chart defaults
            # to blue, a third accent fighting the green theme.
            st.bar_chart(chart_df, x="Count", y="Industry", color="#3DB985",
                         horizontal=True, height=220)


# ── Insurance / Reinsurance details ──────────────────────────────────
# The hunt is anchored on insurance / reinsurance leadership roles, so the
# bar above is only half the story — the concrete rows behind that bar are
# what's actionable. Surface them.

_insur_re = _INDUSTRY_RULES[0][1]  # (label, pattern) — first entry is Insurance / Reinsurance


def _is_insurance(row) -> bool:
    blob = " ".join(safe_str(row.get(k)) for k in ("company", "role", "notes"))
    return bool(_insur_re.search(blob))


_insur_rows = worklist[worklist.apply(_is_insurance, axis=1)].copy() if not worklist.empty else worklist.iloc[0:0]

if not _insur_rows.empty:
    with st.container(border=True):
        st.markdown(f"**Insurance / Reinsurance roles · {len(_insur_rows)}**")
        st.caption("Rows where company / role / notes mention insurance, reinsurance, insurtech, underwriting, claims, or actuarial work.")

        _insur_view = _insur_rows[["num", "company", "role", "score", "status", "job_url"]].copy()
        _insur_view["salary"] = _insur_view["num"].map(_salary_map).fillna("")
        # Resolved posting date if we know it, otherwise the tracker add-date.
        _insur_view["posted"] = _insur_view["num"].map(_posted_map).fillna("")
        _insur_view["added"] = _insur_rows["date"].dt.strftime("%Y-%m-%d").fillna("")
        _insur_view["date"] = _insur_view.apply(
            lambda r: r["posted"] or r["added"] or "",
            axis=1,
        )
        _insur_view = _insur_view.drop(columns=["posted", "added"])
        _insur_view["open"] = _insur_view["num"].apply(lambda n: f"/role?num={int(n)}")

        _insur_view = _insur_view.rename(columns={
            "num": "#", "company": "Company", "role": "Role", "score": "Score",
            "status": "Status", "job_url": "JD link", "salary": "Salary",
            "date": "Date", "open": "Review",
        })
        _insur_view = _insur_view.sort_values(
            "Score", ascending=False, na_position="last",
        )[["#", "Review", "Company", "Role", "Score", "Salary", "Status", "JD link", "Date"]]

        st.dataframe(
            _insur_view,
            use_container_width=True,
            hide_index=True,
            height=min(360, 60 + 36 * len(_insur_view)),
            column_config={
                "Review":  st.column_config.LinkColumn("Review", display_text="open →", width="small"),
                "JD link": st.column_config.LinkColumn("JD link", display_text="JD ↗",   width="small"),
                "Score":   st.column_config.NumberColumn("Score", format="%.1f / 5"),
                "Salary":  st.column_config.TextColumn("Salary", width="small"),
                "Date":    st.column_config.TextColumn("Date",   width="small"),
            },
        )
