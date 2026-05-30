"""Tests for services.cv_templates — registry loader for CV template picker."""

from __future__ import annotations

import json

from services import cv_templates


def test_registry_loads_from_repo():
    tpls = cv_templates.list_templates()
    assert len(tpls) >= 1
    slugs = {t.slug for t in tpls}
    # The 5 templates shipped with the picker MVP.
    assert "classic" in slugs
    assert {"editorial", "executive", "modern", "minimalist"}.issubset(slugs)


def test_registry_files_exist_on_disk():
    """Every entry in cv-templates.json must point at a real HTML file —
    otherwise the picker would let users select a template that the worker
    cannot load."""
    from services import project_root
    tpl_dir = project_root() / "templates"
    for tpl in cv_templates.list_templates():
        path = tpl_dir / tpl.file
        assert path.exists(), f"Missing template file: {path}"


def test_default_slug_resolves_to_known_entry():
    slug = cv_templates.default_slug()
    known = {t.slug for t in cv_templates.list_templates()}
    assert slug in known


def test_get_returns_none_for_unknown_slug():
    assert cv_templates.get("does-not-exist") is None
    assert cv_templates.get("") is None
    assert cv_templates.get(None) is None


def test_get_returns_template_for_known_slug():
    tpl = cv_templates.get("classic")
    assert tpl is not None
    assert tpl.slug == "classic"
    assert tpl.file.endswith(".html")


def test_fallback_when_registry_missing(tmp_path, monkeypatch):
    """If the registry file is gone, we still return the classic fallback so
    the dashboard stays usable."""
    monkeypatch.setattr(cv_templates, "_registry_path", lambda: tmp_path / "missing.json")
    tpls = cv_templates.list_templates()
    assert len(tpls) == 1
    assert tpls[0].slug == "classic"


def test_fallback_when_registry_malformed(tmp_path, monkeypatch):
    bad = tmp_path / "bad.json"
    bad.write_text("{not json", encoding="utf-8")
    monkeypatch.setattr(cv_templates, "_registry_path", lambda: bad)
    tpls = cv_templates.list_templates()
    assert tpls[0].slug == "classic"


def test_entries_missing_required_fields_are_skipped(tmp_path, monkeypatch):
    payload = {
        "default": "classic",
        "templates": [
            {"slug": "classic", "label": "ATS Classic", "file": "cv-template.html"},
            {"slug": "broken"},  # missing label and file — must be dropped
            {"label": "No slug", "file": "x.html"},  # missing slug — drop
        ],
    }
    p = tmp_path / "reg.json"
    p.write_text(json.dumps(payload), encoding="utf-8")
    monkeypatch.setattr(cv_templates, "_registry_path", lambda: p)
    tpls = cv_templates.list_templates()
    assert len(tpls) == 1
    assert tpls[0].slug == "classic"


def test_single_eval_request_accepts_template():
    """The picker passes a template slug into the eval request."""
    from services import single_eval
    req = single_eval.SingleEvalRequest(
        num=1, url="https://x", company="ACME", role="Lead",
        template="editorial",
    )
    assert req.template == "editorial"


def test_single_eval_request_template_defaults_empty():
    from services import single_eval
    req = single_eval.SingleEvalRequest(num=1, url="https://x", company="ACME", role="Lead")
    assert req.template == ""


# ── Visual preview rendering ────────────────────────────────────────────

def test_render_example_html_fills_every_template():
    """Each registered template renders to HTML with no leftover {{PLACEHOLDER}}
    tokens and recognizable example content."""
    import re
    for tpl in cv_templates.list_templates():
        html = cv_templates.render_example_html(tpl.slug)
        assert html, f"No preview HTML for {tpl.slug}"
        # The bundled example person must appear.
        assert "Alex Chen" in html
        # No unresolved placeholders should remain.
        assert not re.search(r"\{\{[A-Z_]+\}\}", html), f"Leftover placeholder in {tpl.slug}"


def test_render_example_html_inlines_fonts_not_relative_paths():
    """The preview iframe can't reach ./fonts/, so font refs must be inlined
    as data URIs (when the fonts dir is present)."""
    from services import project_root
    html = cv_templates.render_example_html("classic")
    assert html is not None
    if (project_root() / "fonts").is_dir():
        assert "url('./fonts/" not in html
        assert "data:font/woff2;base64," in html


def test_render_example_html_none_for_unknown_slug():
    assert cv_templates.render_example_html("does-not-exist") is None
    assert cv_templates.render_example_html(None) is None


def test_render_example_html_none_when_file_missing(tmp_path, monkeypatch):
    """A registry entry pointing at a missing file yields None, not a crash."""
    import json
    payload = {
        "default": "ghost",
        "templates": [
            {"slug": "ghost", "label": "Ghost", "file": "nope-does-not-exist.html"},
        ],
    }
    p = tmp_path / "reg.json"
    p.write_text(json.dumps(payload), encoding="utf-8")
    monkeypatch.setattr(cv_templates, "_registry_path", lambda: p)
    assert cv_templates.render_example_html("ghost") is None


def test_render_example_html_strips_empty_certifications():
    """The empty certifications block must not leave a dangling section."""
    html = cv_templates.render_example_html("classic")
    assert html is not None
    assert "<!-- CERTIFICATIONS -->" not in html
