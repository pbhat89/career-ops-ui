"""Desk — landing. Hero + bulk-action cards + worklist + below-fold widgets."""

from __future__ import annotations

import datetime as dt
import re

import pandas as pd
import streamlit as st

try:
    import yaml  # type: ignore
except Exception:  # pragma: no cover — graceful degradation if pyyaml missing
    yaml = None

try:
    from streamlit_autorefresh import st_autorefresh
except ImportError:
    st_autorefresh = None  # graceful fallback

from services import tracker, batch, runner, styling, project_root, interest, reports
from services.ui_helpers import safe_str, has_value, status_badge_html, score_badge_html

styling.inject()


# ── Helpers ────────────────────────────────────────────────────────────

_EXPIRED_HINTS = re.compile(r"\b(closed|expired|posting expired|withdrawn|filled)\b", re.IGNORECASE)
INACTIVE_STATUSES = {"Discarded", "SKIP", "Rejected"}

# Keys on a tracked_companies[] entry that mean scan.mjs can hit a real API.
_API_KEYS = ("greenhouse", "ashby", "lever", "workday", "smartrecruiters")
_API_METHODS = {"greenhouse_api", "ashby_api", "lever_api", "api"}


def _count_portal_apis() -> tuple[int, int]:
    """Return (api_enabled, total_enabled) tracked companies from portals.yml.

    api_enabled = companies with a Greenhouse/Ashby/Lever-style endpoint
    `scan.mjs` can actually hit. Falls back gracefully if pyyaml or the
    file is unavailable.
    """
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
    total = 0
    with_api = 0
    for c in companies:
        if not isinstance(c, dict):
            continue
        if c.get("enabled") is False:
            continue
        total += 1
        if any(c.get(k) for k in _API_KEYS):
            with_api += 1
            continue
        method = str(c.get("scan_method") or "").lower()
        if method in _API_METHODS:
            with_api += 1
    return with_api, total


def _is_expired_row(row) -> bool:
    if row.get("status") in INACTIVE_STATUSES:
        return True
    note = safe_str(row.get("notes"))
    if note and _EXPIRED_HINTS.search(note):
        return True
    return False


def _last_scan_info() -> tuple[str, int]:
    hist = project_root() / "data" / "scan-history.tsv"
    if not hist.exists():
        return "never", 0
    try:
        sh = pd.read_csv(hist, sep="\t")
        if "first_seen" not in sh.columns:
            return "unknown", 0
        latest = sh["first_seen"].max()
        new_count = int((sh["first_seen"] == latest).sum())
        return str(latest), new_count
    except Exception:
        return "unknown", 0


def _greeting() -> str:
    h = dt.datetime.now().hour
    if h < 5:   return "Late night"
    if h < 12:  return "Good morning"
    if h < 18:  return "Good afternoon"
    return "Good evening"


def _candidate_first_name() -> str:
    """Read first name from config/profile.yml; blank if unavailable."""
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
last_scan, scan_new = _last_scan_info()

n_total = len(df)
n_pending_total = int((df["status"] == "Pending").sum()) if not df.empty else 0
pending_with_url = batch.evaluable_pending(df) if not df.empty else df
n_evaluable = len(pending_with_url)

_first_name = _candidate_first_name()
_hero_greeting = f"{_greeting()}, {_first_name}" if _first_name else _greeting()
st.markdown(
    f'''
    <div class="hero-card">
        <h1>{_hero_greeting}</h1>
        <div class="hero-sub">
            {n_total} apps tracked · {n_evaluable} ready to evaluate · last scan
            <strong>{last_scan}</strong> ({scan_new} new on that date)
        </div>
    </div>
    ''',
    unsafe_allow_html=True,
)


# ── Bulk action cards ──────────────────────────────────────────────────

st.markdown('<div class="section-label">Bulk actions</div>', unsafe_allow_html=True)
ac1, ac2, ac3 = st.columns(3, gap="medium")

with ac1:
    with st.container(border=True):
        st.markdown(
            f'<div style="font-size:0.78rem;color:var(--tx3);text-transform:uppercase;letter-spacing:0.06em;margin-bottom:6px;">Evaluate</div>'
            f'<div style="color:var(--tx);font-weight:600;font-size:1.05rem;margin-bottom:4px;">{n_evaluable} pending</div>'
            f'<div style="color:var(--tx2);font-size:0.85rem;margin-bottom:14px;">Score, report, PDF, cover letter for every row with a JD URL.</div>',
            unsafe_allow_html=True,
        )
        if st.button("Run evaluation", type="primary", use_container_width=True, disabled=(n_evaluable == 0), key="bulk_eval_btn"):
            st.session_state["show_eval_dialog"] = True

with ac2:
    with st.container(border=True):
        st.markdown(
            '<div style="font-size:0.78rem;color:var(--tx3);text-transform:uppercase;letter-spacing:0.06em;margin-bottom:6px;">Scan</div>'
            '<div style="color:var(--tx);font-weight:600;font-size:1.05rem;margin-bottom:4px;">Portals</div>'
            '<div style="color:var(--tx2);font-size:0.85rem;margin-bottom:14px;">Greenhouse · Ashby · Lever · efinancialcareers · MyCareersFuture.</div>',
            unsafe_allow_html=True,
        )
        if st.button("Open scanner", use_container_width=True, key="bulk_scan_btn"):
            st.session_state["show_scan_dialog"] = True

with ac3:
    with st.container(border=True):
        n_expired = int(df.apply(_is_expired_row, axis=1).sum()) if not df.empty else 0
        st.markdown(
            f'<div style="font-size:0.78rem;color:var(--tx3);text-transform:uppercase;letter-spacing:0.06em;margin-bottom:6px;">Tidy</div>'
            f'<div style="color:var(--tx);font-weight:600;font-size:1.05rem;margin-bottom:4px;">{n_expired} expired postings</div>'
            f'<div style="color:var(--tx2);font-size:0.85rem;margin-bottom:14px;">Mark closed/withdrawn postings as Discarded.</div>',
            unsafe_allow_html=True,
        )
        if st.button("Tidy expired", use_container_width=True, key="bulk_tidy_btn", disabled=(n_expired == 0)):
            moved = 0
            if not df.empty:
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


# ── Dialogs ────────────────────────────────────────────────────────────

@st.dialog("Evaluate pending offers", width="large")
def evaluate_dialog(rows: pd.DataFrame):
    st.write(f"This will run **{len(rows)}** evaluation(s) — each produces a score, report, tailored PDF, and cover letter.")
    st.caption("Each evaluation calls `claude -p` (uses Claude Max subscription tokens). Runs in background; UI stays usable.")

    st.dataframe(
        rows[["num", "company", "role", "job_url"]].rename(columns={
            "num": "#", "company": "Company", "role": "Role", "job_url": "URL",
        }),
        hide_index=True,
        use_container_width=True,
        height=240,
        column_config={"URL": st.column_config.LinkColumn("URL", display_text="open")},
    )

    parallel = st.slider("Parallel workers", 1, 4, 1, help="More = faster but more concurrent token use.")
    dry_run = st.checkbox("Dry run (no actual evaluation, just show what would run)", value=False)

    c1, c2 = st.columns(2)
    if c1.button("Cancel", use_container_width=True):
        st.session_state["show_eval_dialog"] = False
        st.rerun()
    if c2.button("Start batch", type="primary", use_container_width=True):
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
            st.toast(f"Batch started (PID {proc.pid}). Watch progress below.", icon="🚀")
            st.rerun()
        except Exception as e:
            st.error(f"Failed to start batch: {e}")


_NEW_OFFER_PATTERNS = (
    re.compile(r"(\d+)\s+new\s+offer", re.IGNORECASE),
    re.compile(r"added\s+(\d+)", re.IGNORECASE),
    re.compile(r"(\d+)\s+added", re.IGNORECASE),
)


def _parse_new_offers(stdout: str) -> int | None:
    """Best-effort count of new offers from scan.mjs stdout. None if unknown."""
    if not stdout:
        return None
    for line in stdout.splitlines()[::-1]:
        for pat in _NEW_OFFER_PATTERNS:
            m = pat.search(line)
            if m:
                try:
                    return int(m.group(1))
                except ValueError:
                    pass
    return None


@st.dialog("Scan portals")
def scan_dialog():
    st.caption("Scan for new roles")

    api_count, _total_count = _count_portal_apis()

    company = st.text_input("Restrict to a company (optional)", placeholder="e.g. Anthropic")
    dry_run = st.checkbox("Dry run (preview only)", value=False)

    c1, c2 = st.columns(2)
    if c1.button("Cancel", use_container_width=True, key="scan_cancel"):
        st.session_state["show_scan_dialog"] = False
        st.rerun()
    run_clicked = c2.button("Run scan", type="primary", use_container_width=True, key="scan_run")

    _ls, _ = _last_scan_info()
    st.caption(f"Last scan: {_ls if _ls else 'never'}")

    if run_clicked:
        with st.spinner("Scanning…"):
            result = runner.scan(dry_run=dry_run, company=company or None)

        stdout = result.stdout or ""
        stderr = result.stderr or ""

        if result.ok:
            new_offers = _parse_new_offers(stdout)
            if new_offers is None and api_count == 0:
                st.error("Scan finished with 0 new offers — no companies have an API endpoint configured.")
            elif new_offers == 0:
                st.warning(
                    "Scan complete — **0 new offers**. "
                    + (
                        "Try adding more API-enabled companies in **Settings → Portals**."
                        if api_count == 0
                        else "Either nothing new was posted, or your title filters excluded everything."
                    )
                )
            elif new_offers and new_offers > 0:
                st.success(f"Scan complete — **{new_offers} new offer(s)** added as Pending.")
            else:
                st.success("Scan complete.")
        else:
            st.error("Scan failed.")

        # Always show output so 1-second silent runs are no longer confusing.
        st.markdown("**Scanner output**")
        body = stdout if stdout.strip() else "(scanner produced no stdout)"
        tail = body.splitlines()[-25:]
        st.code("\n".join(tail) if tail else body, language="text")
        if stderr.strip():
            with st.expander("stderr", expanded=not result.ok):
                st.code(stderr[-2000:], language="text")

        st.cache_data.clear()


if st.session_state.get("show_eval_dialog") and not df.empty:
    evaluate_dialog(pending_with_url)
if st.session_state.get("show_scan_dialog"):
    scan_dialog()


# ── Batch progress (tqdm-style, auto-refreshes while active) ─────────

# Auto-merge any completed evaluations into applications.md so the worklist
# reflects fresh scores/reports without manual `node merge-tracker.mjs`.
_merged_count = batch.auto_merge_if_pending()
if _merged_count > 0:
    st.cache_data.clear()  # force tracker to re-read applications.md
    # Reload df NOW so the worklist below picks up the freshly-merged rows
    # without waiting for the next autorefresh tick (cuts streaming latency
    # from ~4s to ~2s while a batch is running).
    df = tracker.load_applications()

state_df = batch.read_state()
if not state_df.empty:
    summary = batch.state_summary()

    # Autorefresh every 2s WHILE batch is active (so progress is live, tqdm-style).
    # Stops on its own once no rows are in_progress/pending.
    if summary["active"] and st_autorefresh is not None:
        st_autorefresh(interval=2000, limit=600, key="batch_autorefresh")

    total = summary["total"] or 1
    done = summary["completed"] + summary["failed"]
    pct = done / total if total else 0
    bar_width = 40
    filled = int(pct * bar_width)
    bar = "█" * filled + "░" * (bar_width - filled)

    status_word = "Running…" if summary["active"] else "Done"
    color = "var(--accent)" if summary["active"] else "#4ADE80"

    st.markdown(
        f'''
        <div style="background:var(--bg-card);border:1px solid var(--bd);border-radius:12px;padding:18px 22px;margin-bottom:16px;">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;">
                <div>
                    <div style="font-size:11px;text-transform:uppercase;letter-spacing:0.08em;color:var(--tx3);">Batch evaluation</div>
                    <div style="color:var(--tx);font-weight:600;font-size:1.1rem;margin-top:2px;">
                        {done}/{summary["total"]} — {int(pct*100)}% · <span style="color:{color};">{status_word}</span>
                    </div>
                </div>
                <div style="display:flex;gap:18px;text-align:right;">
                    <div><div style="font-size:11px;color:var(--tx3);text-transform:uppercase;letter-spacing:0.06em;">In flight</div><div style="color:var(--tx);font-weight:600;font-size:1.1rem;">{summary["in_progress"]}</div></div>
                    <div><div style="font-size:11px;color:var(--tx3);text-transform:uppercase;letter-spacing:0.06em;">Failed</div><div style="color:{"var(--status-rejected)" if summary["failed"] else "var(--tx)"};font-weight:600;font-size:1.1rem;">{summary["failed"]}</div></div>
                </div>
            </div>
            <div style="font-family:'JetBrains Mono',monospace;font-size:14px;letter-spacing:0;color:{color};line-height:1.2;">{bar}</div>
        </div>
        ''',
        unsafe_allow_html=True,
    )

    # Currently-processing ticker
    processing = batch.currently_processing()
    if processing:
        st.markdown('<div class="section-label">Now evaluating</div>', unsafe_allow_html=True)
        for r in processing[:3]:
            rid = r.get("id", "?")
            ru = (r.get("url", "") or "")[:90]
            st.markdown(
                f'<div style="background:var(--bg-elev);border-left:3px solid var(--accent);border-radius:6px;'
                f'padding:8px 12px;margin-bottom:6px;color:var(--tx2);font-size:0.85rem;">'
                f'<span style="color:var(--tx);font-weight:600;">#{rid}</span> · {ru}</div>',
                unsafe_allow_html=True,
            )

    # Live log tail
    log_name, log_tail = batch.latest_log_tail(n_lines=12)
    if log_tail:
        with st.expander(f"📜 Live log — {log_name}", expanded=summary["active"]):
            st.code(log_tail, language="text")

    # Per-row detail
    with st.expander("Per-row batch worker status (id, started, finished, score, error)", expanded=False):
        st.caption("Each row is one `claude -p` worker. Updated as workers finish — newest at top.")
        display_state = state_df[["id", "status", "started_at", "completed_at", "report_num", "score", "error"]].copy()
        st.dataframe(display_state.tail(50)[::-1], use_container_width=True, hide_index=True)

    # Reset button (visible once batch is no longer active)
    if not summary["active"]:
        if st.button("Clear batch state", key="clear_batch_state", help="Removes batch-input.tsv and batch-state.tsv so this strip disappears."):
            (project_root() / "batch" / "batch-state.tsv").unlink(missing_ok=True)
            (project_root() / "batch" / "batch-input.tsv").unlink(missing_ok=True)
            st.toast("Batch state cleared.", icon="🧹")
            st.rerun()


# ── Worklist ───────────────────────────────────────────────────────────

if df.empty:
    st.stop()

wc1, wc2, wc3, wc4 = st.columns([2.4, 1.4, 1.2, 1.0])
wc1.markdown("##### Worklist")
sort_choice = wc2.selectbox(
    "Sort ↑↓",
    ["Smart (default)", "Score (high→low)", "Score (low→high)", "Date (newest)", "Status (legacy)"],
    label_visibility="visible",
    key="worklist_sort",
    help="Smart: Evaluated high-score first, watchlist & inactive sink to the bottom.",
)
hide_no = wc3.toggle("Hide 'No' interest", value=True, help="Hide rows you've marked as not interested.")
show_inactive = wc4.toggle("Show inactive", value=False, help="Include Discarded / SKIP / Rejected / expired postings.")

# Annotate with interest (from data/interest.tsv, keyed by row num)
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

# ── Column filters (Status / Company / Score / Date) ─────────────────
# Canonical states from templates/states.yml + "Pending"/"Watchlist" seen
# in status_order, plus "In progress" (live batch overlay).
_status_options = [
    "Pending", "Watchlist", "Evaluated", "In progress", "Applied",
    "Responded", "Interview", "Offer", "Rejected", "Discarded", "SKIP",
]

# Bounds for the date picker — fall back to today if column has no values.
_dates = pd.to_datetime(worklist["date"], errors="coerce").dropna()
if not _dates.empty:
    _date_min = _dates.min().date()
    _date_max = _dates.max().date()
else:
    _date_max = dt.date.today()
    _date_min = _date_max

fc1, fc2, fc3, fc4 = st.columns([1.4, 1.4, 1.6, 1.6])
filter_status = fc1.multiselect(
    "Status", options=_status_options, default=st.session_state.get("filter_status", []),
    key="filter_status", placeholder="Any status",
)
_company_options = sorted(
    {str(c) for c in worklist["company"].dropna().astype(str) if str(c).strip()}
)
filter_company = fc2.multiselect(
    "Company", options=_company_options,
    default=st.session_state.get("filter_company", []),
    key="filter_company", placeholder="Any company",
)
filter_score = fc3.slider(
    "Score range", 0.0, 5.0,
    value=st.session_state.get("filter_score", (0.0, 5.0)),
    step=0.1, key="filter_score",
)
filter_score_unscored = fc3.checkbox(
    "Include unscored", value=st.session_state.get("filter_score_unscored", True),
    key="filter_score_unscored",
)
filter_date = fc4.date_input(
    "Date range", value=st.session_state.get("filter_date", (_date_min, _date_max)),
    min_value=_date_min, max_value=_date_max, key="filter_date",
)

# Apply filters (skip each one when at "no filter" default).
if filter_status:
    # Match on the post-overlay status, but here we only have raw status —
    # the live "In progress" overlay is applied later, so honor that label
    # by including rows whose num appears in the live in-progress map.
    _statuses_set = set(filter_status)
    _wanted_in_progress = "In progress" in _statuses_set
    _other_statuses = _statuses_set - {"In progress"}
    if _wanted_in_progress and not state_df.empty and "id" in state_df.columns and "status" in state_df.columns:
        _in_progress_ids = {
            int(br["id"])
            for _, br in state_df.iterrows()
            if str(br.get("status", "")).lower() in ("processing", "in_progress")
            and pd.notna(br.get("id"))
        }
    else:
        _in_progress_ids = set()
    mask = worklist["status"].isin(_other_statuses)
    if _in_progress_ids:
        mask = mask | worklist["num"].isin(_in_progress_ids)
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

# date_input returns a tuple when range is selected; a single date if user picked one day.
if isinstance(filter_date, tuple) and len(filter_date) == 2:
    _df_lo, _df_hi = filter_date
    if not (_df_lo == _date_min and _df_hi == _date_max):
        _wd = pd.to_datetime(worklist["date"], errors="coerce")
        worklist = worklist[(_wd.dt.date >= _df_lo) & (_wd.dt.date <= _df_hi)]

if sort_choice == "Score (high→low)":
    worklist = worklist.sort_values(["score", "date"], ascending=[False, False], na_position="last")
elif sort_choice == "Score (low→high)":
    worklist = worklist.sort_values(["score", "date"], ascending=[True, False], na_position="last")
elif sort_choice == "Date (newest)":
    worklist = worklist.sort_values("date", ascending=False, na_position="last")
elif sort_choice == "Status (legacy)":
    worklist = worklist.sort_values(["__sort", "date"], ascending=[True, False])
else:
    # Smart sort: Evaluated (score desc) → active pipeline (score desc) →
    # Watchlist (date desc) → everything else (status order, date desc).
    def _smart_group(s: str) -> int:
        if s == "Evaluated": return 0
        if s in ("Applied", "Responded", "Interview", "Offer"): return 1
        if s == "Watchlist": return 2
        return 3
    worklist = worklist.copy()
    worklist["__group"] = worklist["status"].map(_smart_group).fillna(3).astype(int)
    worklist = worklist.sort_values(
        ["__group", "score", "__sort", "date"],
        ascending=[True, False, True, False],
        na_position="last",
    )
    worklist = worklist.drop(columns=["__group"])

worklist = worklist.drop(columns=["__sort", "__expired"])

worklist_view = worklist[["num", "company", "role", "score", "status", "has_pdf", "job_url", "date", "report_path", "__interest"]].copy()
worklist_view["added_date"] = worklist_view["date"].dt.strftime("%Y-%m-%d")
worklist_view["job_url"] = worklist_view["job_url"].fillna("").replace("", None)

# Parse posted_date + salary_raw from each row's report (when one exists).
# Cheap on-disk read per row; reports are short and st.cache_data on the page
# keeps repeat renders fast within the same session.
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

# Date column = JD posted date when known; tracker date with "(added)" otherwise.
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

# Overlay live batch state on the Status column: rows currently being
# evaluated show "In progress"; rows that just completed show "Evaluated".
# "completed" only overlays when the row actually has a merged score —
# otherwise merge-tracker.mjs may have routed the report to a different
# tracker row (e.g. company/role rename), and the original row should
# keep its real applications.md status (typically "Pending").
_batch_state_map: dict[int, str] = {}
if not state_df.empty and "id" in state_df.columns and "status" in state_df.columns:
    for _, br in state_df.iterrows():
        try:
            _id = int(br["id"])
        except (TypeError, ValueError):
            continue
        bs = str(br.get("status", "")).lower()
        if bs in ("processing", "in_progress"):
            _batch_state_map[_id] = "In progress"
        elif bs == "failed":
            _batch_state_map[_id] = "Failed"
        elif bs == "completed":
            _batch_state_map[_id] = "Evaluated"  # gated below by score presence

if _batch_state_map:
    def _overlay(r):
        target = _batch_state_map.get(int(r["num"]))
        if target is None:
            return r["status"]
        # For "completed" entries, only overlay when the row has a real
        # score in applications.md. Otherwise the merge didn't land here
        # and overlaying "Evaluated" would mislead the user.
        if target == "Evaluated":
            sc = r.get("score")
            if sc is None or (isinstance(sc, float) and pd.isna(sc)):
                return r["status"]
        return target
    worklist_view["status"] = worklist_view.apply(_overlay, axis=1)

worklist_view = worklist_view.rename(columns={
    "num": "#", "company": "Company", "role": "Role", "score": "Score",
    "status": "Status", "has_pdf": "PDF", "job_url": "JD link", "date": "Date",
    "salary": "Salary",
})

# Add a Select column for the action bar; track Interest separately (inline-editable).
worklist_view.insert(0, "Select", False)
worklist_view = worklist_view[["Select", "#", "Company", "Role", "Score", "Salary", "Status", "PDF", "JD link", "Date", "Interest"]]

# data_editor: Select + Interest are inline-editable; everything else read-only.
edited_view = st.data_editor(
    worklist_view,
    use_container_width=True,
    hide_index=True,
    height=440,
    key="worklist_table",
    disabled=["#", "Company", "Role", "Score", "Salary", "Status", "PDF", "JD link", "Date"],
    column_config={
        "Select": st.column_config.CheckboxColumn("☐", help="Tick rows for the action bar below.", width="small", default=False),
        "JD link": st.column_config.LinkColumn("JD link", display_text="open posting", width="small"),
        "Score": st.column_config.NumberColumn("Score", format="%.1f / 5", help="—  = not evaluated yet"),
        "Salary": st.column_config.TextColumn(
            "Salary", width="small",
            help="Estimated comp band — from the evaluation report. Blank = not mentioned in JD.",
        ),
        "Date": st.column_config.TextColumn(
            "Date", width="small",
            help="JD posting date when known; falls back to the date the row was added.",
        ),
        "PDF": st.column_config.CheckboxColumn("PDF", width="small"),
        "Interest": st.column_config.SelectboxColumn(
            "Interest",
            options=["", "Yes", "No"],
            help="Mark whether you want to pursue this role. Saved per role (not per company).",
            width="small",
        ),
    },
)

# Persist any Interest changes back to data/interest.tsv
if edited_view is not None and not edited_view.empty:
    for _, r in edited_view.iterrows():
        try:
            n = int(r["#"])
        except (TypeError, ValueError):
            continue
        new_val = "" if r["Interest"] is None else str(r["Interest"]).strip()
        if new_val not in ("", "Yes", "No"):
            continue
        if _interest_map.get(n, "") != new_val:
            try:
                interest.set_interest(n, new_val)
            except Exception:
                pass

# Derive selection from the Select column.
picked_nums_direct: list[int] = []
if edited_view is not None and "Select" in edited_view.columns:
    for _, r in edited_view.iterrows():
        if bool(r.get("Select")):
            try:
                picked_nums_direct.append(int(r["#"]))
            except (TypeError, ValueError):
                pass
st.caption("Tick **Select** to add a row to the action bar · set **Interest = Yes/No** to filter your worklist · sort with the dropdown above")

# ── Contextual action bar (visible only when 1+ rows are checked) ──────
picked_nums = picked_nums_direct
if picked_nums:
    # Map back to the full worklist DataFrame so we get job_url + raw fields for evaluate_dialog.
    picked_full = worklist[worklist["num"].isin(picked_nums)].copy()
    all_have_url = bool(len(picked_full)) and picked_full["job_url"].fillna("").astype(str).str.strip().ne("").all()

    st.markdown(
        f'<div style="color:var(--tx2);font-size:0.85rem;margin:8px 0 6px;">'
        f'<strong>{len(picked_nums)}</strong> selected'
        f'</div>',
        unsafe_allow_html=True,
    )
    ab0, ab1, ab2, ab3, _ = st.columns([1.4, 1.6, 1.6, 1.0, 3.4])

    # REVIEW — single-row drill-in (uses st.switch_page for same-tab navigation).
    # Primary CTA when exactly one row is selected; still available with multi-select
    # but reads "Review #{first}" and clarifies the behaviour via help text.
    review_help = (
        "Open this role's full evaluation report."
        if len(picked_nums) == 1
        else "Reviews the first-selected row."
    )
    review_label = f"Review #{picked_nums[0]}"
    if ab0.button(
        review_label,
        type="primary",
        use_container_width=True,
        key="worklist_open_btn",
        help=review_help,
    ):
        st.session_state.selected_num = picked_nums[0]
        st.switch_page("pages/role.py")

    if ab1.button(
        f"Evaluate {len(picked_nums)} selected",
        type="primary",
        use_container_width=True,
        disabled=not all_have_url,
        help=None if all_have_url else "Every selected row needs a JD URL to evaluate.",
        key="worklist_bulk_eval",
    ):
        evaluate_dialog(picked_full)

    if ab2.button(
        "Mark selected → Discarded",
        use_container_width=True,
        key="worklist_bulk_discard",
    ):
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

    if ab3.button("Clear selection", use_container_width=True, key="worklist_bulk_clear"):
        # Resetting the data_editor's key drops its edit state (including Select ticks).
        st.session_state.pop("worklist_table", None)
        st.rerun()


# ── Below the fold ─────────────────────────────────────────────────────

# Industry classifier — first match wins. "Other / Unsure" is the fallback;
# we keep it in the chart as a smaller bucket so the user sees uncategorised
# volume rather than silently hiding it.
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
        st.caption("Pie equivalent — bars sized by count.")
        ind_series = worklist.apply(_classify_industry, axis=1) if not worklist.empty else pd.Series(dtype=str)
        if ind_series.empty:
            st.caption("No rows to classify.")
        else:
            counts = ind_series.value_counts()
            chart_df = counts.rename_axis("Industry").reset_index(name="Count")
            st.bar_chart(chart_df, x="Industry", y="Count", height=200)
