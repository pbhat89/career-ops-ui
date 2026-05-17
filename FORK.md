# career-ops-ui — personal fork by [@pbhat89](https://github.com/pbhat89)

A working copy of [santifer/career-ops](https://github.com/santifer/career-ops) with a Streamlit web dashboard, English-translated agent modes, a merge-tracker bug fix, and a few quality-of-life UX tweaks.

Personal data (CV, profile, reports, scan history, generated CVs, application tracker) is in `.gitignore` and stays local. Everything in this repo is reusable by anyone — fork it, drop your own `cv.md` + `config/profile.yml` + `portals.yml` in place, and the system runs against your own data.

---

## What's new vs upstream

### `dashboard-web/` — Streamlit dashboard (new)

A click-driven web UI on `http://localhost:8765` that reads the same source-of-truth files as the Go TUI in `dashboard/` (no separate database). Launch with `career-dashboard-web.bat` on Windows — first run creates a venv under `dashboard-web/.venv/` and installs deps.

What it does:

- **Desk** — landing page with KPIs (Jobs Found / High-fit ≥4.3 / Industry match), a worklist with per-column filters (Status / Company / Score / Date), a Smart-sort default (Evaluated by score desc, then Applied/Responded/Interview/Offer, then Watchlist, then everything else), and a contextual action bar (Review · Evaluate selected · Mark Discarded · Clear).
- **Role** — drill-in for a single offer. PDF preview rendered server-side via `pymupdf` (works over Cloudflare tunnels — no Chrome data-URI blocking). Status changer, JD-link, downloads (PDF + cover letter), and inline report rendering.
- **Signals** — patterns & cadence overview.
- **Settings popover** (sidebar) — inline editors for `profile.yml`, `portals.yml`; Doctor / Verify-pipeline diagnostics; data refresh button.
- **Industry mix** below the fold (Insurance/Reinsurance · Banking · Consulting · Tech/SaaS · Government/Public · Other).
- **Optional email gate** — set `CAREEROPS_AUTH_EMAIL=you@email` before launch and the dashboard requires that email to unlock. Off by default. Pairs well with `cloudflared tunnel --url http://localhost:8765` if you need mobile access.
- **Batch progress strip** — tqdm-style live progress while `batch-runner.sh` is processing, with auto-merge of completed tracker-additions and orphan-Pending row cleanup (rows whose URL was evaluated under a different tracker row are auto-discarded with a breadcrumb).

The dashboard is a UI layer only. All real work still goes through the `.mjs` scripts, the batch runner, and `merge-tracker.mjs` — same data contract as upstream.

### `modes/` — English translations

The agent modes (`oferta.md`, `ofertas.md`, `pdf.md`, `pipeline.md`, `scan.md`, `tracker.md`, `training.md`, `project.md`, `contacto.md`, `deep.md`, `auto-pipeline.md`) plus `batch/batch-prompt.md` are translated from Spanish to English. Default language stays English; the upstream Spanish modes are preserved under `modes/es/` if/when added. Other localized modes from upstream (`modes/de/`, `modes/fr/`, `modes/ja/`, `modes/pt/`, `modes/ru/`) are unchanged.

### `merge-tracker.mjs` — score-parser fix

`parseScore("-/5")` was returning `5` (matching the regex on the denominator), which made every Pending row look like a perfect score and broke `shouldUpdate` comparisons during merge. Now returns `null` for `-/5` / `N/A` / `DUP` / empty, with strict-improvement logic in the duplicate-merge branch. Status advance is also preserved — `Applied`/`Interview`/`Offer` rows don't regress to `Evaluated` on a re-eval.

### `career-dashboard-web.bat` — Windows launcher

One-click venv-init + `streamlit run` for users who don't want to copy-paste `python -m streamlit run dashboard-web/app.py`.

---

## What's in `.gitignore` (personal — stays local)

Everything in the project's **User Layer** per `CLAUDE.md`'s data contract:

- `cv.md`, `config/profile.yml`, `portals.yml`, `modes/_profile.md`
- `data/applications.md`, `data/pipeline.md`, `data/scan-history.tsv`, `data/interest.tsv`
- `reports/*.md`, `output/*`, `interview-prep/*`
- `article-digest.md`, `initial-leads.md`
- `batch/cv-*.html` (per-eval tailored CVs), `batch/gen-*.mjs` (per-eval personalize scripts), `batch/logs/*`, `batch/batch-state.tsv`, `batch/batch-input.tsv`, `batch/tracker-additions/**/*.tsv`
- `dashboard-web/.venv/`, `dashboard-web/**/__pycache__/`, `dashboard-web/*.log`
- `dashboard/career-dashboard.exe` (built locally; the Go source under `dashboard/` is tracked)

If you fork this repo, drop your own files in those paths and they'll stay local to your clone.

---

## Setup (TL;DR for a new clone)

```bash
git clone https://github.com/pbhat89/career-ops-ui.git
cd career-ops-ui

# 1. Your CV + profile + targeting
cp config/profile.example.yml config/profile.yml         # edit
cp templates/portals.example.yml portals.yml             # edit target companies
cp modes/_profile.template.md modes/_profile.md          # your archetype + narrative
# write your cv.md by hand or paste your LinkedIn into Claude Code and let it generate

# 2. Node side (scan, eval, merge)
npm install

# 3. Web dashboard (Python)
career-dashboard-web.bat        # Windows
# or: python -m venv dashboard-web/.venv && dashboard-web/.venv/Scripts/python -m pip install -r dashboard-web/requirements.txt
#     python -m streamlit run dashboard-web/app.py
```

Then open `http://localhost:8765`.

---

## Credit + license

All credit to **[@santifer](https://github.com/santifer)** — the original system, the agent design, the 6 archetype scoring, the `modes/` library, the `dashboard/` Go TUI, the entire pipeline. This fork only adds a web UI and translates the prompts. Upstream license (MIT) applies to everything; my contributions inherit the same.

Pull upstream updates with:

```bash
git remote add upstream https://github.com/santifer/career-ops.git
git fetch upstream
git merge upstream/main
```
