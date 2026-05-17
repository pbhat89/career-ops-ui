"""Tests for services.reports."""

from __future__ import annotations

from services import reports


def test_parse_report_extracts_header_fields(temp_root):
    r = reports.parse_report("reports/001-hsbc-2026-05-02.md")
    assert r is not None
    assert r.date == "2026-05-02"
    assert r.score == "4.5/5"
    assert r.url == "https://example.com/hsbc-dao"
    assert r.archetype == "Head of Analytics / Data"
    assert "Expired" in r.legitimacy
    assert r.pdf == "output/cv-hsbc-2026-05-02.pdf"
    assert r.cover_letter == "output/cover-letter-hsbc-2026-05-02.md"


def test_parse_report_extracts_tldr(temp_root):
    r = reports.parse_report("reports/001-hsbc-2026-05-02.md")
    assert "HSBC" in r.tldr


def test_parse_report_returns_none_for_missing(temp_root):
    assert reports.parse_report("reports/does-not-exist.md") is None


def test_report_body_returns_full_text(temp_root):
    body = reports.report_body("reports/001-hsbc-2026-05-02.md")
    assert "Role Summary" in body
    assert body.startswith("# Evaluation: HSBC")


def test_list_reports_returns_all(temp_root):
    out = reports.list_reports()
    assert len(out) == 1
    assert out[0].title.startswith("Evaluation: HSBC")
