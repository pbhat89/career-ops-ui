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
