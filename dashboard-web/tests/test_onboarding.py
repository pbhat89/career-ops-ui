"""Unit tests for the onboarding wizard's pure-logic layer.

These exercise services/onboarding.py without spinning up Streamlit —
the wizard UI itself is exercised manually via the dashboard.

Each test uses ``temp_root`` (from conftest.py) so the project layout is
sandboxed and no real user files are touched.
"""

from __future__ import annotations

import io
from pathlib import Path

import pytest

from services import onboarding as ob


# ── is_first_run / missing_user_files ────────────────────────────────

def test_is_first_run_true_on_bare_tmp(temp_root: Path):
    """Bare fixture has none of cv.md / profile.yml / portals.yml /
    _profile.md, so the wizard must fire."""
    assert ob.is_first_run(root=temp_root) is True
    missing = ob.missing_user_files(root=temp_root)
    # All four user-layer files should be flagged.
    assert set(missing) == set(ob.USER_LAYER_FILES)


def test_is_first_run_false_when_all_present(temp_root: Path):
    """Once every user-layer file exists, the wizard must NOT fire."""
    (temp_root / "cv.md").write_text("# CV", encoding="utf-8")
    (temp_root / "config").mkdir(exist_ok=True)
    (temp_root / "config" / "profile.yml").write_text("candidate: {}", encoding="utf-8")
    (temp_root / "modes").mkdir(exist_ok=True)
    (temp_root / "modes" / "_profile.md").write_text("# profile", encoding="utf-8")
    (temp_root / "portals.yml").write_text("tracked_companies: []", encoding="utf-8")

    assert ob.is_first_run(root=temp_root) is False
    assert ob.missing_user_files(root=temp_root) == []


def test_is_first_run_true_when_only_one_missing(temp_root: Path):
    """Missing ONE file is enough to trigger the wizard."""
    (temp_root / "cv.md").write_text("# CV", encoding="utf-8")
    (temp_root / "config").mkdir(exist_ok=True)
    (temp_root / "config" / "profile.yml").write_text("candidate: {}", encoding="utf-8")
    (temp_root / "modes").mkdir(exist_ok=True)
    (temp_root / "modes" / "_profile.md").write_text("# profile", encoding="utf-8")
    # portals.yml deliberately absent
    assert ob.is_first_run(root=temp_root) is True
    assert ob.missing_user_files(root=temp_root) == ["portals.yml"]


# ── State + builders ────────────────────────────────────────────────

def _full_state() -> ob.OnboardingState:
    """A populated state object that exercises every save_all branch."""
    s = ob.OnboardingState(
        cv_markdown="# Prateek Bhatnagar\n\nAnalytics leader in APAC insurance.",
        full_name="Prateek Bhatnagar",
        email="prateek@example.com",
        phone="+65 0000 0000",
        location="Singapore, Singapore",
        timezone="Asia/Singapore",
        linkedin="linkedin.com/in/prateek",
        portfolio_url="https://prateek.example",
        github="github.com/prateek",
        visa_status="Singapore PR — no sponsorship needed",
        target_titles=["Head of AI", "Head of Data", "Chief AI Officer"],
        archetype_fit={
            "ai_platform": "primary",
            "agentic": "secondary",
            "ai_pm": "skip",
            "ai_sa": "secondary",
            "ai_fde": "skip",
        },
        salary_currency="SGD",
        salary_minimum=300_000,
        salary_target_low=400_000,
        salary_target_high=600_000,
        remote_preference="hybrid",
        regional_preference=["Singapore", "APAC"],
        company_enabled=ob.default_company_state(),
        custom_companies=["Munich Re", "Trust Bank"],
        superpower="APAC analytics ops at scale; 90-day AI ship cycles.",
        excites_drains="Excited: ambiguous big bets. Drains: lift-and-shift.",
        dealbreakers="No rigid 5-day on-site. No startups under 20.",
    )
    return s


def test_save_all_writes_every_expected_file(temp_root: Path):
    """All six target files exist after save_all, with sensible content."""
    state = _full_state()
    # Disable a couple of companies so the toggle path is exercised.
    state.company_enabled["Anthropic"] = False

    written = ob.save_all(state, root=temp_root)

    # All keys present
    expected = {"cv", "profile_yml", "profile_md", "portals",
                "applications", "pipeline"}
    assert set(written) == expected

    # Every path exists and is non-empty
    for label, path in written.items():
        assert path.exists(), f"{label} not written: {path}"
        assert path.read_text(encoding="utf-8").strip(), \
            f"{label} written empty: {path}"

    # cv.md round-trips
    assert "Prateek Bhatnagar" in (temp_root / "cv.md").read_text(encoding="utf-8")

    # profile.yml mentions name + currency + target title
    profile_text = (temp_root / "config" / "profile.yml").read_text(encoding="utf-8")
    assert "Prateek Bhatnagar" in profile_text
    assert "SGD" in profile_text
    assert "Head of AI" in profile_text

    # _profile.md captures archetype primary + dealbreakers
    profile_md = (temp_root / "modes" / "_profile.md").read_text(encoding="utf-8")
    assert "AI Platform" in profile_md or "AI Platform / LLMOps" in profile_md
    assert "No rigid 5-day on-site" in profile_md

    # applications.md / pipeline.md are the empty headers
    apps = (temp_root / "data" / "applications.md").read_text(encoding="utf-8")
    assert apps.startswith("# Applications Tracker")
    pipe = (temp_root / "data" / "pipeline.md").read_text(encoding="utf-8")
    assert pipe.startswith("# Pipeline — Inbox")


def test_save_all_preserves_existing_tracker(temp_root: Path):
    """save_all must NOT overwrite an existing applications.md — that
    file is sacred (it has the user's real history)."""
    # conftest.temp_root already creates a populated applications.md
    original = (temp_root / "data" / "applications.md").read_text(encoding="utf-8")
    assert "HSBC" in original  # sanity check on the fixture

    ob.save_all(_full_state(), root=temp_root)

    after = (temp_root / "data" / "applications.md").read_text(encoding="utf-8")
    assert after == original, "save_all clobbered an existing tracker"


def test_build_portals_disables_unchecked_company(temp_root: Path):
    """When the user unticks a company in step 6, the resulting
    portals.yml must mark that company as enabled: false."""
    # We need the template to be present so the builder can find it.
    templates_dir = temp_root / "templates"
    templates_dir.mkdir(parents=True, exist_ok=True)
    # Minimal template containing one entry we can flip.
    (templates_dir / "portals.example.yml").write_text(
        "title_filter:\n"
        "  positive:\n"
        "    - \"AI\"\n"
        "  negative:\n"
        "    - \"Junior\"\n"
        "\n"
        "search_queries: []\n"
        "\n"
        "tracked_companies:\n"
        "  - name: Anthropic\n"
        "    careers_url: https://job-boards.greenhouse.io/anthropic\n"
        "    enabled: true\n"
        "\n"
        "  - name: OpenAI\n"
        "    careers_url: https://openai.com/careers\n"
        "    enabled: true\n",
        encoding="utf-8",
    )

    state = ob.OnboardingState(
        target_titles=["Head of AI"],
        company_enabled={"Anthropic": False, "OpenAI": True},
    )
    yaml_text = ob._build_portals_yaml(state, root=temp_root)

    # Anthropic's enabled flag must be flipped to false; OpenAI stays true.
    # The Anthropic block comes first — the line right after careers_url.
    anth_idx = yaml_text.index("- name: Anthropic")
    open_idx = yaml_text.index("- name: OpenAI")
    anth_block = yaml_text[anth_idx:open_idx]
    open_block = yaml_text[open_idx:]

    assert "enabled: false" in anth_block, anth_block
    assert "enabled: true" in open_block, open_block

    # Custom titles win the positive-titles section
    assert '- "Head of AI"' in yaml_text


def test_build_portals_falls_back_when_template_missing(temp_root: Path):
    """No templates/portals.example.yml on disk — builder must still
    produce a valid skeleton instead of crashing."""
    # temp_root has no templates/ dir at all
    state = ob.OnboardingState(
        target_titles=["Head of Data"],
        custom_companies=["Munich Re"],
    )
    yaml_text = ob._build_portals_yaml(state, root=temp_root)

    assert "Head of Data" in yaml_text
    assert "Munich Re" in yaml_text
    assert "tracked_companies:" in yaml_text


def test_default_company_state_all_enabled():
    """Every catalogue entry starts ticked — matches the wizard's UI."""
    state = ob.default_company_state()
    assert state, "default_company_state returned empty"
    assert all(v is True for v in state.values())
    # Spot-check categories are flattened in
    assert "Anthropic" in state
    assert "n8n" in state


def test_pdf_to_markdown_extracts_text():
    """Round-trip a tiny in-memory PDF through PyMuPDF and confirm we
    get the text back. Skipped if pymupdf isn't installed in this env."""
    pytest.importorskip("fitz")
    import fitz  # PyMuPDF

    # Build a 1-page PDF with one line of text.
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "Hello from CV PDF")
    buf = io.BytesIO(doc.tobytes())
    doc.close()

    out = ob.pdf_to_markdown(buf)
    assert "Hello" in out
    assert "PDF" in out


def test_atomic_write_overwrites_existing(temp_root: Path):
    """_atomic_write is used everywhere; confirm it replaces in place."""
    target = temp_root / "tmpfile.md"
    ob._atomic_write(target, "first")
    ob._atomic_write(target, "second")
    assert target.read_text(encoding="utf-8") == "second"
    # No leftover .tmp sibling
    assert not list(temp_root.glob("tmpfile.md.tmp"))
