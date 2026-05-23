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


def test_extract_block_a(temp_root):
    block_a = reports.extract_block("reports/001-hsbc-2026-05-02.md", "A")
    assert block_a.startswith("## A) Role Summary")
    assert "TL;DR" in block_a
    # Block A must NOT include the next block
    assert "## B)" not in block_a


def test_extract_block_b(temp_root):
    block_b = reports.extract_block("reports/001-hsbc-2026-05-02.md", "B")
    assert block_b.startswith("## B) CV Match")
    assert "Requirement" in block_b
    assert "## C)" not in block_b


def test_extract_block_d_compensation(temp_root):
    block_d = reports.extract_block("reports/001-hsbc-2026-05-02.md", "D")
    assert block_d.startswith("## D) Compensation")
    assert "SGD" in block_d


def test_extract_block_f_interview(temp_root):
    block_f = reports.extract_block("reports/001-hsbc-2026-05-02.md", "F")
    assert block_f.startswith("## F) Interview Plan")
    assert "STAR" in block_f
    # Block F must not bleed into G
    assert "## G)" not in block_f


def test_extract_block_g_legitimacy(temp_root):
    block_g = reports.extract_block("reports/001-hsbc-2026-05-02.md", "G")
    assert block_g.startswith("## G) Posting Legitimacy")
    assert "Proceed" in block_g
    # Block G must not include Global Score
    assert "## Global Score" not in block_g


def test_extract_global_score(temp_root):
    gs = reports.extract_global_score("reports/001-hsbc-2026-05-02.md")
    assert gs.startswith("## Global Score")
    assert "APPLY HIGH" in gs


def test_extract_block_invalid_letter_returns_empty(temp_root):
    assert reports.extract_block("reports/001-hsbc-2026-05-02.md", "Z") == ""


def test_extract_block_missing_file_returns_empty(temp_root):
    assert reports.extract_block("reports/nope.md", "A") == ""
