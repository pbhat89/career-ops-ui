# dashboard-web

Streamlit dashboard for career-ops — a click-driven alternative to the Go TUI in `dashboard/`.

## Run

```cmd
career-dashboard-web.bat
```

The first run creates a venv at `dashboard-web/.venv` and installs dependencies. Subsequent launches reuse it. Opens on http://localhost:8765.

## What it does

Three top-nav pages plus a sidebar command palette.

- **Desk** (landing) — greeting + freshness banner, Quick-action cards (Paste JD ·
  Scan · Inbox · Evaluate · Tidy expired · Diagnostics), live batch-evaluation
  progress, and the **Worklist**: every application, filterable by status / company /
  score / date, sortable (Smart / Score / Date / Status), with single-click row
  drill-in and multi-row select for bulk Evaluate / Compare / Discard. Below the
  fold: follow-ups due, recent reports, industry mix.
- **Role** — single-application drill-in. Hero (company · role · status · score),
  the evaluation split across tabs (Overview · JD Match · Comp & Demand · Tailoring ·
  Interview · Legitimacy · Raw), an Actions panel (generate / re-evaluate, CV-template
  picker, PDF preview + downloads, LaTeX export, status / interest), and one-click
  generation of Apply / Outreach / Deep / Interview-prep prompts to `output/prompts/`.
- **Signals** — Funnel + score distribution, rejection-pattern detector, follow-up
  cadence, scan history, and a Lab for standalone Training / Project evaluations.
- **Sidebar** — KPIs (Jobs Found · High-fit · Industry match), the command palette
  (routes every action through the Desk dialogs), and a **Settings** popover to edit
  `config/profile.yml` / `portals.yml` and run `doctor` / `verify-pipeline`.

## Auto-refresh

When you come back after time away, the sidebar offers to (and on a second launch, automatically does):

1. Re-scan portals if last scan > 3 days
2. Liveness-check JD URLs on Applied/Interview rows
3. Recompute follow-up cadence
4. Re-run pattern analysis

The first launch on a fresh machine **skips** this and shows your existing data as-is.

## Architecture

```
dashboard-web/
├── app.py              # entry: sidebar (KPIs + command palette + Settings),
│                       #   onboarding gate, auto-refresh, st.navigation router
├── pages/              # registered via st.navigation() in app.py
│   ├── desk.py         # landing: quick actions, dialogs, worklist, signals
│   ├── role.py         # single-application drill-in
│   ├── signals.py      # funnel / patterns / scan history / lab
│   └── _onboarding.py  # first-run setup wizard (not in the nav)
├── services/
│   ├── tracker.py      # parse + mutate applications.md / pipeline.md
│   ├── reports.py      # parse reports/*.md (header + blocks A–G)
│   ├── runner.py       # subprocess wrapper for the .mjs scripts
│   ├── batch.py        # parallel evaluation orchestrator + state
│   ├── single_eval.py  # one-row evaluation
│   ├── refresh.py      # cold-start / auto-refresh orchestrator
│   ├── cv_templates.py # CV template registry
│   ├── interest.py     # per-row Yes/No interest store
│   ├── styling.py      # injected CSS (source of truth for the palette)
│   └── ui_helpers.py   # pills, badges, status strip, KPI tiles
└── .streamlit/config.toml   # native-widget theme — keep in sync with styling.py
```

**Hard rule:** pages never touch files directly — they go through `services/`, which respect the data contract (`data/applications.md` is source of truth, new entries via `merge-tracker.mjs`, etc.).

## Why Streamlit + subprocess instead of porting to Python?

The `.mjs` scripts already work, are tested by `test-all.mjs`, and are the contract Claude Code uses. Re-implementing them in Python would create two sources of truth and double the maintenance. The Streamlit layer is a UI, not a rewrite.
