"""First-run onboarding wizard — pure logic.

The Streamlit page imports these helpers; this module knows nothing about
Streamlit so it can be unit-tested without a browser session.

Public surface
--------------
- ``is_first_run()`` -> bool
  Returns True if any of the four user-layer files is missing:
    * ``cv.md`` (project root)
    * ``config/profile.yml``
    * ``modes/_profile.md``
    * ``portals.yml``
  When *all four* exist the wizard never fires.

- ``missing_user_files()`` -> list[str]
  Same check but returns the human-readable paths that are absent. Used by
  step 1 of the wizard so the user knows why they're here.

- ``OnboardingState`` dataclass
  Held in ``st.session_state`` across reruns. Mutable; each step writes
  its own slice.

- ``save_all(state, *, root=None)`` -> dict
  Writes every output file atomically. Returns a dict of the absolute
  paths that were created/updated. Raises on any error so the wizard can
  surface it.

- ``pdf_to_markdown(file_like)`` -> str
  Best-effort PDF→markdown conversion. Uses PyMuPDF (already in
  requirements.txt as ``pymupdf``) when available; otherwise raises with
  a helpful message. Output is plain text wrapped to roughly mimic
  markdown — multi-column CV layouts are notoriously hard to extract
  cleanly, so the wizard always shows the result in an editable textarea
  before saving.

The helpers ``_build_profile_yaml``, ``_build_profile_md``,
``_build_portals_yaml`` are exposed for unit tests but not part of the
stable contract.
"""

from __future__ import annotations

import io
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import IO, Optional

from . import project_root

# ── User-layer file inventory ─────────────────────────────────────────

USER_LAYER_FILES = (
    "cv.md",
    "config/profile.yml",
    "modes/_profile.md",
    "portals.yml",
)


# Defaults for step 4 (chips). Pulled from config/profile.example.yml but
# trimmed and broadened so the wizard works for any role family. The user
# can deselect/extend in the UI.
DEFAULT_TARGET_TITLES = [
    "Head of AI",
    "Head of Data",
    "Head of Analytics",
    "Chief AI Officer",
    "Chief Data Officer",
    "Director of AI",
    "Director of Data",
    "VP Data Science",
    "VP Analytics",
    "Senior AI Engineer",
    "Staff ML Engineer",
    "AI Product Manager",
    "Solutions Architect (AI)",
    "Forward Deployed Engineer",
    "AI Transformation Lead",
]


# Five archetypes shown in step 4. Each is a (key, title, blurb).
DEFAULT_ARCHETYPES = [
    ("ai_platform", "AI Platform / LLMOps Engineer",
     "Evaluation, observability, pipelines, reliability in production."),
    ("agentic", "Agentic Workflows / Automation",
     "HITL, tooling, orchestration, multi-agent systems."),
    ("ai_pm", "Technical AI Product Manager",
     "PRDs, discovery, GenAI/Agents, delivery."),
    ("ai_sa", "AI Solutions Architect",
     "Enterprise integrations, hyperautomation, end-to-end design."),
    ("ai_fde", "AI Forward Deployed Engineer",
     "Client-facing, rapid prototyping, prototype-to-prod."),
]


# Step 5 currency options
CURRENCY_OPTIONS = [
    "USD", "EUR", "GBP", "SGD", "HKD", "AUD", "JPY", "INR", "CAD", "CHF",
]

# Step 5 regional options
REGION_OPTIONS = [
    "Singapore", "APAC", "EU", "UK", "US", "Canada", "Middle East",
    "LATAM", "Global / Remote-Anywhere",
]

# Step 5 remote modes
REMOTE_OPTIONS = ["onsite", "hybrid", "remote", "flexible"]


# ── Public helpers ────────────────────────────────────────────────────

def _root(override: Optional[Path] = None) -> Path:
    return Path(override) if override else project_root()


def missing_user_files(root: Optional[Path] = None) -> list[str]:
    """Return the user-layer files that don't exist on disk."""
    base = _root(root)
    return [rel for rel in USER_LAYER_FILES if not (base / rel).exists()]


def is_first_run(root: Optional[Path] = None) -> bool:
    """True if any of the user-layer files is missing — wizard should fire."""
    return bool(missing_user_files(root))


# ── State ─────────────────────────────────────────────────────────────

@dataclass
class OnboardingState:
    """Carried across Streamlit reruns via ``st.session_state``."""

    # Step 2 — CV
    cv_markdown: str = ""

    # Step 3 — profile basics
    full_name: str = ""
    email: str = ""
    phone: str = ""
    location: str = ""
    timezone: str = "Asia/Singapore"
    linkedin: str = ""
    portfolio_url: str = ""
    github: str = ""
    visa_status: str = ""

    # Step 4 — target roles + archetypes
    target_titles: list[str] = field(default_factory=list)
    # archetype_key -> "primary" | "secondary" | "skip"
    archetype_fit: dict[str, str] = field(default_factory=dict)

    # Step 5 — compensation + location
    salary_currency: str = "USD"
    salary_minimum: int = 0
    salary_target_low: int = 0
    salary_target_high: int = 0
    remote_preference: str = "flexible"
    regional_preference: list[str] = field(default_factory=list)

    # Step 6 — companies (name -> bool). Custom entries get appended to
    # ``custom_companies`` and shown alongside the defaults.
    company_enabled: dict[str, bool] = field(default_factory=dict)
    custom_companies: list[str] = field(default_factory=list)

    # Step 7 — narrative (all optional)
    superpower: str = ""
    excites_drains: str = ""
    dealbreakers: str = ""

    def archetype_primary_names(self) -> list[str]:
        return [
            title
            for key, title, _ in DEFAULT_ARCHETYPES
            if self.archetype_fit.get(key) == "primary"
        ]

    def archetype_secondary_names(self) -> list[str]:
        return [
            title
            for key, title, _ in DEFAULT_ARCHETYPES
            if self.archetype_fit.get(key) == "secondary"
        ]


# ── PDF → markdown ────────────────────────────────────────────────────

def pdf_to_markdown(file_like: IO[bytes]) -> str:
    """Best-effort PDF → markdown via PyMuPDF.

    Multi-column CVs and design-heavy templates won't round-trip cleanly —
    the wizard always lets the user edit the output before saving, so this
    is a starting point, not a finished artifact.
    """
    try:
        import fitz  # PyMuPDF, ships as 'pymupdf' on PyPI
    except ImportError as e:  # pragma: no cover - exercised in CI without pymupdf
        raise RuntimeError(
            "PyMuPDF (pymupdf) is required to import a PDF. "
            "Run: pip install pymupdf"
        ) from e

    data = file_like.read() if hasattr(file_like, "read") else file_like
    if isinstance(data, str):
        data = data.encode("utf-8")

    out: list[str] = []
    with fitz.open(stream=data, filetype="pdf") as doc:
        for page in doc:
            text = page.get_text("text") or ""
            # Collapse 3+ blank lines into 2, strip trailing whitespace
            text = re.sub(r"\n{3,}", "\n\n", text.strip())
            if text:
                out.append(text)
    raw = "\n\n".join(out)
    return raw.strip() or "# Your CV\n\n_(PDF extraction returned no text — paste your CV manually here.)_\n"


# ── Default CV template (step 2 "build from scratch") ─────────────────

CV_SCRATCH_TEMPLATE = """\
# Your Name

your@email · +country-phone · City, Country · linkedin.com/in/yourhandle

## Summary

One-paragraph headline. Who you are, what you build, the impact you've shipped.

## Experience

### Company — Role (YYYY-MM – Present)

- Achievement with metric.
- Achievement with metric.

### Previous Company — Role (YYYY-MM – YYYY-MM)

- Achievement with metric.

## Projects

- **Project name** — what it does, link, hero metric.

## Education

- Degree, University, Year

## Skills

Comma-separated list grouped by theme (languages, platforms, domains).
"""


# ── YAML builders ─────────────────────────────────────────────────────

def _yaml_str(value: str) -> str:
    """Single-line double-quoted YAML string (escape `"` and `\\`)."""
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def _yaml_list(values: list[str], indent: int = 4) -> str:
    if not values:
        return f"{' ' * indent}[]"
    pad = " " * indent
    return "\n".join(f"{pad}- {_yaml_str(v)}" for v in values)


def _build_profile_yaml(state: OnboardingState) -> str:
    """Render config/profile.yml from wizard state."""

    primary_titles = state.target_titles or ["Senior AI Engineer"]
    archetype_blocks: list[str] = []
    for key, name, _ in DEFAULT_ARCHETYPES:
        fit = state.archetype_fit.get(key, "skip")
        if fit == "skip":
            continue
        archetype_blocks.append(
            "    - name: " + _yaml_str(name) + "\n"
            "      level: " + _yaml_str("Senior/Staff/Head") + "\n"
            "      fit: " + _yaml_str(fit)
        )
    if not archetype_blocks:
        archetype_blocks.append(
            "    - name: " + _yaml_str("AI/ML Engineer") + "\n"
            "      level: " + _yaml_str("Senior/Staff") + "\n"
            "      fit: " + _yaml_str("primary")
        )

    superpowers = [s.strip() for s in re.split(r"[\n;,]", state.superpower) if s.strip()]
    if not superpowers and state.superpower.strip():
        superpowers = [state.superpower.strip()]

    target_range_str = ""
    if state.salary_target_low and state.salary_target_high:
        target_range_str = f"{state.salary_currency} {state.salary_target_low:,}-{state.salary_target_high:,}"
    elif state.salary_target_low:
        target_range_str = f"{state.salary_currency} {state.salary_target_low:,}+"
    minimum_str = (
        f"{state.salary_currency} {state.salary_minimum:,}"
        if state.salary_minimum else ""
    )

    location_flex = {
        "onsite": "On-site preferred",
        "hybrid": "Hybrid (2-3 days in office)",
        "remote": "Remote-first",
        "flexible": "Flexible — open to onsite, hybrid, or remote",
    }.get(state.remote_preference, "Flexible")

    regions_clause = ", ".join(state.regional_preference) if state.regional_preference else "Open"

    lines = [
        "# Career-Ops Profile Configuration",
        "# Generated by the dashboard onboarding wizard. Edit freely.",
        "",
        "candidate:",
        "  full_name: " + _yaml_str(state.full_name),
        "  email: " + _yaml_str(state.email),
        "  phone: " + _yaml_str(state.phone),
        "  location: " + _yaml_str(state.location),
        "  linkedin: " + _yaml_str(state.linkedin),
        "  portfolio_url: " + _yaml_str(state.portfolio_url),
        "  github: " + _yaml_str(state.github),
        "",
        "target_roles:",
        "  primary:",
        _yaml_list(primary_titles, indent=4),
        "  archetypes:",
        "\n".join(archetype_blocks),
        "",
        "narrative:",
        "  headline: " + _yaml_str(state.superpower.splitlines()[0] if state.superpower else ""),
        "  exit_story: " + _yaml_str(state.excites_drains),
        "  superpowers:",
        _yaml_list(superpowers, indent=4) if superpowers else "    []",
        "  dealbreakers: " + _yaml_str(state.dealbreakers),
        "",
        "compensation:",
        "  target_range: " + _yaml_str(target_range_str),
        "  currency: " + _yaml_str(state.salary_currency),
        "  minimum: " + _yaml_str(minimum_str),
        "  location_flexibility: " + _yaml_str(location_flex),
        "  regional_preference: " + _yaml_str(regions_clause),
        "",
        "location:",
        "  country: " + _yaml_str(state.location.split(",")[-1].strip() if state.location else ""),
        "  city: " + _yaml_str(state.location.split(",")[0].strip() if state.location else ""),
        "  timezone: " + _yaml_str(state.timezone),
        "  visa_status: " + _yaml_str(state.visa_status),
        "  remote_preference: " + _yaml_str(state.remote_preference),
        "",
        "cv:",
        '  output_format: "html"',
        "",
    ]
    return "\n".join(lines)


def _build_profile_md(state: OnboardingState) -> str:
    """Render modes/_profile.md from wizard state (substitute into template)."""

    primary_archetypes = state.archetype_primary_names()
    secondary_archetypes = state.archetype_secondary_names()

    title_list = "\n".join(f"- {t}" for t in state.target_titles) or "- (none specified yet)"

    primary_block = "\n".join(f"- **{n}**" for n in primary_archetypes) or "- _(none — set a primary archetype)_"
    secondary_block = "\n".join(f"- {n}" for n in secondary_archetypes) or "- _(none)_"

    superpowers = state.superpower.strip() or "_(fill this in when you have time — what's your signature move?)_"
    excites = state.excites_drains.strip() or "_(what kind of work makes you light up? what drains you?)_"
    dealbreakers = state.dealbreakers.strip() or "_(no rigid on-site policies / no startups under 20 people / etc.)_"

    target_range = (
        f"{state.salary_currency} {state.salary_target_low:,}-{state.salary_target_high:,}"
        if state.salary_target_low and state.salary_target_high
        else "_(set in config/profile.yml)_"
    )
    minimum = (
        f"{state.salary_currency} {state.salary_minimum:,}"
        if state.salary_minimum else "_(set in config/profile.yml)_"
    )

    location_policy = {
        "onsite": "On-site preferred. Score remote-only roles down unless the team is exceptional.",
        "hybrid": "Hybrid (2-3 days in office) is the sweet spot.",
        "remote": "Remote-first. Score forced-onsite roles down.",
        "flexible": "Flexible — open to onsite, hybrid, or remote.",
    }.get(state.remote_preference, "Flexible.")

    return f"""# User Profile Context — career-ops

<!-- ============================================================
     THIS FILE IS YOURS. It will NEVER be auto-updated.

     Customize everything here: archetypes, narrative, proof
     points, negotiation scripts, location policy.

     Initially generated by the dashboard onboarding wizard
     ({_safe_date()}). Edit freely.
     ============================================================ -->

## Your Target Roles

{title_list}

### Primary archetypes

{primary_block}

### Secondary archetypes

{secondary_block}

## Your Superpower

{superpowers}

## What Excites / Drains You

{excites}

## Deal-breakers

{dealbreakers}

## Your Comp Targets

- **Target range:** {target_range}
- **Minimum (walk-away):** {minimum}
- **Currency:** {state.salary_currency}

## Your Location Policy

- **Base:** {state.location or '_(set in config/profile.yml)_'}
- **Timezone:** {state.timezone}
- **Visa status:** {state.visa_status or '_(set in config/profile.yml)_'}
- **Remote preference:** {state.remote_preference}
- **Regions of interest:** {', '.join(state.regional_preference) if state.regional_preference else '_(open)_'}
- **Policy:** {location_policy}

## Your Negotiation Scripts

**Salary expectations:**
> "Based on market data for this role, I'm targeting {target_range}. I'm flexible on structure — what matters is the total package and the opportunity."

**When offered below target:**
> "I'm comparing with opportunities in the higher range. I'm drawn to [company] because of [reason]. Can we explore [target]?"
"""


def _safe_date() -> str:
    # Pulled out so tests can monkeypatch it deterministically if needed.
    import datetime as _dt
    return _dt.date.today().isoformat()


def _build_portals_yaml(state: OnboardingState, *, root: Optional[Path] = None) -> str:
    """Build portals.yml — start from templates/portals.example.yml, apply
    company toggles, append custom additions, and override title_filter.positive
    from the user's target titles when they supplied any."""

    base_path = _root(root) / "templates" / "portals.example.yml"
    if not base_path.exists():
        # Fallback when running tests in a minimal tmp_path — emit a
        # functioning skeleton so save_all() doesn't crash.
        return _portals_skeleton(state)

    text = base_path.read_text(encoding="utf-8")

    # 1. Re-write title_filter.positive if the user gave us titles.
    if state.target_titles:
        text = _replace_positive_titles(text, state.target_titles)

    # 2. Apply company toggles. The defaults file ships almost everything
    # as enabled: true; for any entry where the user un-ticked the
    # checkbox we flip the company's `enabled:` line to false.
    for company, enabled in state.company_enabled.items():
        text = _set_company_enabled(text, company, enabled)

    # 3. Append any custom companies the user typed in. We don't know
    # their careers_url, so we leave a TODO marker the user can fill in.
    if state.custom_companies:
        addition = ["", "  # -- Custom additions (added during onboarding) --"]
        for name in state.custom_companies:
            addition.extend([
                "",
                f"  - name: {name}",
                f"    careers_url: https://example.com/  # TODO: replace with real careers URL",
                f"    scan_method: websearch",
                f"    scan_query: '\"{name}\" careers jobs'",
                f"    enabled: true",
            ])
        text = text.rstrip() + "\n" + "\n".join(addition) + "\n"

    return text


def _replace_positive_titles(text: str, titles: list[str]) -> str:
    """Swap title_filter.positive list for user-provided titles."""
    pattern = re.compile(
        r"(title_filter:\s*\n\s*positive:\s*\n)(?:\s*#[^\n]*\n|\s*-\s*[^\n]*\n)+",
        re.MULTILINE,
    )
    new_list = "\n".join(f"    - {t!r}" for t in titles).replace("'", '"')
    replacement = "title_filter:\n  positive:\n" + new_list + "\n"
    if pattern.search(text):
        return pattern.sub(replacement, text, count=1)
    return text  # Nothing to replace — leave as-is.


def _set_company_enabled(text: str, company_name: str, enabled: bool) -> str:
    """Flip the `enabled:` line inside the tracked_companies entry whose
    `- name:` matches *company_name*. Idempotent."""
    # Block = from "- name: <name>" up to the next blank line or next "- name:".
    escaped = re.escape(company_name)
    pattern = re.compile(
        rf"(^\s+- name:\s*{escaped}\s*$.*?)(^\s+enabled:\s*)(true|false)([^\n]*)$",
        re.MULTILINE | re.DOTALL,
    )
    new_flag = "true" if enabled else "false"

    def _repl(m: re.Match) -> str:
        return f"{m.group(1)}{m.group(2)}{new_flag}{m.group(4)}"

    return pattern.sub(_repl, text, count=1)


def _portals_skeleton(state: OnboardingState) -> str:
    titles = state.target_titles or ["AI", "ML", "LLM"]
    positive = "\n".join(f"    - {t!r}".replace("'", '"') for t in titles)
    custom = ""
    for name in state.custom_companies:
        custom += (
            f"\n  - name: {name}\n"
            f"    careers_url: https://example.com/  # TODO\n"
            f"    scan_method: websearch\n"
            f"    scan_query: '\"{name}\" careers jobs'\n"
            f"    enabled: true\n"
        )
    return f"""# Generated by the dashboard onboarding wizard.
title_filter:
  positive:
{positive}
  negative:
    - "Junior"
    - "Intern"

search_queries: []

tracked_companies:{custom or '  []'}
"""


# ── Tracker / pipeline scaffolds ──────────────────────────────────────

APPLICATIONS_HEADER = """# Applications Tracker

| # | Date | Company | Role | Score | Status | PDF | Report | Notes |
|---|------|---------|------|-------|--------|-----|--------|-------|
"""

PIPELINE_HEADER = """# Pipeline — Inbox

## Pending

"""


# ── save_all ──────────────────────────────────────────────────────────

def save_all(
    state: OnboardingState,
    *,
    root: Optional[Path] = None,
) -> dict[str, Path]:
    """Write every output file. Returns {logical_name: absolute_path}.

    Writing order (matters for partial-failure recovery):
      1. cv.md
      2. config/profile.yml
      3. modes/_profile.md
      4. portals.yml
      5. data/applications.md  (only if missing)
      6. data/pipeline.md      (only if missing)

    Steps 1-4 always overwrite; steps 5-6 are header-only and idempotent.
    """
    base = _root(root)
    written: dict[str, Path] = {}

    cv_path = base / "cv.md"
    cv_text = state.cv_markdown.strip() or CV_SCRATCH_TEMPLATE
    _atomic_write(cv_path, cv_text + ("\n" if not cv_text.endswith("\n") else ""))
    written["cv"] = cv_path

    profile_yml = base / "config" / "profile.yml"
    profile_yml.parent.mkdir(parents=True, exist_ok=True)
    _atomic_write(profile_yml, _build_profile_yaml(state))
    written["profile_yml"] = profile_yml

    profile_md = base / "modes" / "_profile.md"
    profile_md.parent.mkdir(parents=True, exist_ok=True)
    _atomic_write(profile_md, _build_profile_md(state))
    written["profile_md"] = profile_md

    portals = base / "portals.yml"
    _atomic_write(portals, _build_portals_yaml(state, root=base))
    written["portals"] = portals

    data_dir = base / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    apps = data_dir / "applications.md"
    if not apps.exists():
        _atomic_write(apps, APPLICATIONS_HEADER)
    written["applications"] = apps

    pipeline = data_dir / "pipeline.md"
    if not pipeline.exists():
        _atomic_write(pipeline, PIPELINE_HEADER)
    written["pipeline"] = pipeline

    return written


def _atomic_write(path: Path, text: str) -> None:
    """Write through a temporary sibling, then replace. Survives crashes."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8", newline="\n")
    tmp.replace(path)


# ── Step 6 default-company catalogue ──────────────────────────────────
#
# Used by the wizard to render checkboxes when portals.yml doesn't exist
# yet. We deliberately do NOT parse templates/portals.example.yml at this
# step — that file is too noisy (~150 entries across 5 markets). Instead
# we expose a curated set, grouped by category, all default-checked.
# Anything the user has *additional* preference for lives in custom_companies.

DEFAULT_COMPANY_CATEGORIES: dict[str, list[str]] = {
    "AI Labs & LLM providers": [
        "Anthropic", "OpenAI", "Cohere", "Mistral AI", "Aleph Alpha",
        "Hugging Face", "Perplexity",
    ],
    "AI Infra & LLMOps": [
        "LangChain", "Pinecone", "Arize AI", "Langfuse", "Weights & Biases (CoreWeave)",
        "Glean", "Lakera",
    ],
    "AI-native platforms (FDE/SA)": [
        "Retool", "Airtable", "Vercel", "Temporal", "Sierra", "Decagon", "Lindy",
    ],
    "Voice / Conversational AI": [
        "PolyAI", "Parloa", "ElevenLabs", "Deepgram", "Hume AI", "Vapi", "Bland AI",
    ],
    "Contact Center / CX AI": [
        "Ada", "LivePerson", "Talkdesk", "Twilio", "Dialpad", "Gong", "Genesys",
        "Salesforce",
    ],
    "No-code / Automation": [
        "n8n", "Zapier", "Make.com (Celonis)", "Boomi", "Clay Labs",
    ],
    "European Tech (EMEA)": [
        "DeepL", "Helsing", "Celonis", "Contentful", "Wayve", "Synthesia",
        "Stability AI", "Faculty",
    ],
    "Fintech": [
        "N26", "Trade Republic", "SumUp", "Qonto",
    ],
    "APAC / Singapore tech": [
        "Trust Bank",
    ],
}


def default_company_state() -> dict[str, bool]:
    """All catalogue companies default to enabled."""
    out: dict[str, bool] = {}
    for names in DEFAULT_COMPANY_CATEGORIES.values():
        for n in names:
            out[n] = True
    return out
