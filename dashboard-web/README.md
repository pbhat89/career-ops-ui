# dashboard-web

Streamlit dashboard for career-ops — a click-driven alternative to the Go TUI in `dashboard/`.

## Run

```cmd
career-dashboard-web.bat
```

The first run creates a venv at `dashboard-web/.venv` and installs dependencies. Subsequent launches reuse it. Opens on http://localhost:8765.

## What it does

- **Pipeline** — every application, filterable, with row-level status changes.
- **Inbox** — pending URLs from `data/pipeline.md`.
- **Scan** — runs `scan.mjs` with live log, shows recent scan history.
- **Report** — structured header + rendered Markdown body for any `reports/*.md`.
- **Patterns** — funnel, score distribution, rejection-pattern detector, follow-up cadence.
- **Settings** — edit `config/profile.yml`, `portals.yml`, `modes/_profile.md`; run `doctor` and `verify-pipeline`.

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
├── app.py              # entry, sidebar, landing
├── pages/              # auto-routed by Streamlit
│   ├── 1_Pipeline.py
│   ├── 2_Inbox.py
│   ├── 3_Scan.py
│   ├── 4_Report.py
│   ├── 5_Patterns.py
│   └── 6_Settings.py
├── services/
│   ├── tracker.py      # parse + mutate applications.md
│   ├── reports.py      # parse reports/*.md
│   ├── runner.py       # subprocess wrapper for .mjs scripts
│   └── refresh.py      # cold-start orchestrator
└── .streamlit/config.toml
```

**Hard rule:** pages never touch files directly — they go through `services/`, which respect the data contract (`data/applications.md` is source of truth, new entries via `merge-tracker.mjs`, etc.).

## Why Streamlit + subprocess instead of porting to Python?

The `.mjs` scripts already work, are tested by `test-all.mjs`, and are the contract Claude Code uses. Re-implementing them in Python would create two sources of truth and double the maintenance. The Streamlit layer is a UI, not a rewrite.
