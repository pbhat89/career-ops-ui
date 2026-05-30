# career-ops-ui

> A personal fork of [**santifer/career-ops**](https://github.com/santifer/career-ops) that adds a **web dashboard**, two extra **zero-token scan providers** (Workday + MyCareersFuture), and a **three-mode portal scanner**, tuned for a Singapore / APAC senior AI & Analytics job search.

<p align="center">
  <img src="https://img.shields.io/badge/fork_of-santifer%2Fcareer--ops-000?style=flat&logo=github" alt="fork of santifer/career-ops">
  <img src="https://img.shields.io/badge/UI-Streamlit-FF4B4B?style=flat&logo=streamlit&logoColor=white" alt="Streamlit">
  <img src="https://img.shields.io/badge/TUI-Go-00ADD8?style=flat&logo=go&logoColor=white" alt="Go TUI">
  <img src="https://img.shields.io/badge/Engine-Node.js-339933?style=flat&logo=node.js&logoColor=white" alt="Node.js">
  <img src="https://img.shields.io/badge/Agent-Claude_Code-000?style=flat&logo=anthropic&logoColor=white" alt="Claude Code">
  <img src="https://img.shields.io/badge/License-MIT-blue.svg" alt="MIT">
</p>

---

## What this is

[career-ops](https://github.com/santifer/career-ops) is an AI job-search pipeline built by [santifer](https://santifer.io) and driven from an AI coding CLI (Claude Code, Gemini, OpenCode…). It evaluates job offers (A–G scoring), generates tailored CVs, scans job portals with **zero LLM tokens** (pure HTTP/JSON against ATS APIs), tracks the pipeline in markdown, and runs batch evaluations.

**This fork keeps the original engine and adds a clickable front-end + more scan reach**, so the whole flow — *scan → see new roles → evaluate → CV/PDF* — can be driven from a browser, not just the agent.

> The upstream project is the source of truth for the core engine and the agent skills. The original README is preserved at [`docs/UPSTREAM_README.md`](docs/UPSTREAM_README.md) and online [here](https://github.com/santifer/career-ops#readme) — read it for the full philosophy, scoring model, and CLI usage.

---

## What I added on top of upstream

| Add-on | Where | Notes |
|---|---|---|
| **Streamlit web dashboard** | [`dashboard-web/`](dashboard-web/) | Desk / Role / Signals pages. Not in upstream. |
| **Workday provider** | [`providers/workday.mjs`](providers/workday.mjs) | Zero-token scan of `*.myworkdayjobs.com` (Prudential, UOB, Swiss Re…) |
| **MyCareersFuture provider** | [`providers/mycareersfuture.mjs`](providers/mycareersfuture.mjs) | Zero-token scan of the SG gov job board API |
| **Three-mode scanner + live log** | [`scan.mjs`](scan.mjs) · [`dashboard-web/pages/desk.py`](dashboard-web/pages/desk.py) | Full sweep · by company · by title, with a streaming progress log and auto-promotion of new roles into the worklist |
| **APAC / insurance portals + title taxonomy** | [`portals.yml`](portals.yml) | My target companies, MyCareersFuture queries, Decision-Management / Insights / Enablement title patterns |
| **English modes** | [`modes/`](modes/) | English-first evaluation/apply prompts |

Everything else — the `.mjs` engine, the agent skills, batch runner, report format, Go TUI — is upstream's. The fork stays mergeable with upstream (`upstream/main` is tracked read-only).

---

## Screenshots

**Desk** — landing page: hero + freshness, quick actions, the worklist (filter / sort / multi-select to evaluate), and signals below the fold.

![Desk](docs/img/ui-desk.png)

**Scan dialog** — the fixed three-mode scanner. Each mode streams a live log and drops new roles into the worklist as *Pending*.

![Scan dialog](docs/img/ui-scan-dialog.png)

**Signals** — funnel, score distribution, rejection patterns, scan history, and a Lab for one-off training/project evaluations.

![Signals](docs/img/ui-signals.png)

**Role** — single-application drill-in: evaluation tabs, CV/PDF generation, status & interest.

![Role](docs/img/ui-role.png)

---

## Quick start

### Prerequisites

- **Node.js 18+** — the scan engine and all `*.mjs` scripts
- **Python 3.10+** — the Streamlit web UI
- **Claude Code** (or another supported CLI) — for evaluations, WebSearch scans, CV generation
- **Go 1.24+** *(optional)* — only if you want to rebuild the terminal UI
- `npm install` once in the repo root (installs `js-yaml`, Playwright, etc.)

### Option A — Web UI (Streamlit) ⭐ recommended

```cmd
career-dashboard-web.bat
```

First run creates a venv at `dashboard-web/.venv` and installs deps; later runs reuse it. Opens at **http://localhost:8765**.

macOS / Linux equivalent:

```bash
python -m venv dashboard-web/.venv
dashboard-web/.venv/bin/pip install -r dashboard-web/requirements.txt
dashboard-web/.venv/bin/python -m streamlit run dashboard-web/app.py --server.port 8765
```

From the UI you can: **Scan** (full sweep / by company / by title), review the worklist, **Evaluate** rows (spawns `claude -p` workers), generate CVs/PDFs, and run diagnostics.

### Option B — Terminal UI (Go TUI)

A keyboard-driven pipeline viewer lives in [`dashboard/`](dashboard/).

```cmd
:: run the prebuilt binary, pointed at the repo root (which holds data/)
dashboard\career-dashboard.exe -path .
```

Rebuild from source:

```bash
cd dashboard
go run . -path ..      # run against the parent repo
# or: go build -o career-dashboard.exe .
```

### Option C — Claude Code (the agent)

Open the repo in Claude Code and talk to it: paste a JD URL to evaluate, or run `/career-ops scan` for a **WebSearch-based** scan (LinkedIn, eFinancialCareers, and the WebSearch-only companies the dashboard's zero-token scanner can't reach). See [`CLAUDE.md`](CLAUDE.md) for all modes.

> **Two scanners, on purpose.** The dashboard "Scan" button runs the **zero-token engine** (ATS APIs only: MyCareersFuture, Workday, Greenhouse…). `site:`-style WebSearch queries (LinkedIn, eFinancialCareers, recruiters) run through **`/career-ops scan` in Claude Code**, because WebSearch needs an LLM to form queries and parse results — see [why](#why-the-scan-button-is-api-only).

---

## Starting fresh (if someone else clones this)

This repo is wired to **my** profile. On a clean clone, you become the user. Two ways to set up:

### Easiest — the onboarding wizard

Launch the web UI (`career-dashboard-web.bat`). If the **user-layer** files are missing, the app opens a **first-run setup wizard** instead of the dashboard — it walks you through CV, profile, target roles, salary, and portals, then writes them.

### Or — let Claude Code onboard you

Open the repo in Claude Code and say *"set me up"*. It runs the same onboarding (per [`CLAUDE.md`](CLAUDE.md) → *First Run — Onboarding*): paste your CV or LinkedIn, give it your name / location / target roles / salary, and it creates the files.

### The user-layer files (yours — never overwritten by updates)

The onboarding creates these from templates. To reset to a fresh profile, delete them and re-run onboarding:

| File | What it holds | Template |
|---|---|---|
| `cv.md` | Your CV (markdown, source of truth) | — |
| `config/profile.yml` | Name, contact, target roles, salary | `config/profile.example.yml` |
| `modes/_profile.md` | Your archetypes / narrative / scoring tweaks | `modes/_profile.template.md` |
| `portals.yml` | Companies + scan queries + title filter | `templates/portals.example.yml` |
| `data/applications.md` | The tracker (worklist) | created empty |
| `article-digest.md` *(optional)* | Proof points from your portfolio | — |

Everything under `data/`, `reports/`, `output/`, `interview-prep/` is yours too. The **system layer** (`*.mjs`, `dashboard-web/`, `modes/_shared.md`, `templates/`) is upstream-updatable — see [`DATA_CONTRACT.md`](DATA_CONTRACT.md). **Rule of thumb: personalization goes in `config/profile.yml` or `modes/_profile.md`, never in `modes/_shared.md`.**

---

## How the scan works

```
portals.yml ── tracked_companies ──► scan.mjs (engine, zero-token) ──► dashboard "Scan" button
            └─ search_queries ───────► /career-ops scan (WebSearch + LLM) ──► Claude Code only
```

The dashboard scanner has three modes (all engine-only):

- **🔄 Full sweep** — every API-backed company, your title filter; new roles since last scan
- **🏢 By company** — one company across all its portals
- **🔎 By title** — find roles matching a title you type (overrides the title filter)

New roles land in the worklist as **Pending** with their JD URL, so you can select and **Evaluate** them straight from the table. Reachable engine sources today: **MyCareersFuture** (broad SG coverage) + **Workday** (Prudential, UOB, Swiss Re) + **Greenhouse** (Trust Bank).

<a id="why-the-scan-button-is-api-only"></a>
**Why the scan button is API-only:** `scan.mjs` is a pure HTTP/JSON process with **no LLM** — that's what makes it free and instant. WebSearch needs an agent to form queries, read snippets, judge relevance, and extract `{title, company, url}` — work only Claude can do. So WebSearch sources (LinkedIn, eFinancialCareers, …) live in `/career-ops scan`, not the button.

---

## Repo layout (fork-specific bits)

```
career-ops-ui/
├── scan.mjs                    # zero-token scanner (+ my --json / --title / 3-mode work)
├── providers/                  # scan engines — workday.mjs + mycareersfuture.mjs are mine
├── portals.yml                 # MY companies + queries + title taxonomy (user layer)
├── dashboard-web/              # MY Streamlit UI (Desk / Role / Signals)
│   ├── app.py                  #   entry: sidebar, onboarding gate, router
│   ├── pages/ · services/      #   pages never touch files directly — go via services/
│   └── README.md               #   UI internals
├── dashboard/                  # upstream Go TUI
├── modes/                      # evaluation/apply prompts (_profile.md = user layer)
├── data/ · reports/ · output/  # YOUR data (gitignored where appropriate)
└── CLAUDE.md / AGENTS.md       # agent instructions + onboarding
```

---

## Credits & license

- Original system, engine, and agent skills: **[santifer/career-ops](https://github.com/santifer/career-ops)** by [santifer](https://santifer.io) — the matching portfolio is open source too: [cv-santiago](https://github.com/santifer/cv-santiago).
- This fork: the Streamlit dashboard, Workday + MyCareersFuture providers, three-mode scanner, and APAC/insurance tuning by **Prateek Bhatnagar**.
- License: **MIT** (inherited from upstream — see [`LICENSE`](LICENSE)).

Updates from upstream pull cleanly: `node update-system.mjs check` (system files only; your CV, profile, tracker, and reports are never touched).
