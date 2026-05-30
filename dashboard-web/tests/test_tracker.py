"""Tests for services.tracker — the application-tracker parser + mutator."""

from __future__ import annotations

import pytest

from services import tracker


def test_load_returns_dataframe_with_expected_columns(temp_root):
    df = tracker.load_applications()
    assert not df.empty
    assert set(["num", "date", "company", "role", "score", "status", "job_url"]).issubset(df.columns)


def test_load_parses_all_fixture_rows(temp_root):
    df = tracker.load_applications()
    assert len(df) == 5
    assert list(df["num"]) == [1, 2, 3, 4, 5]


def test_score_parsed_as_float(temp_root):
    df = tracker.load_applications()
    hsbc = df[df["num"] == 1].iloc[0]
    assert hsbc["score"] == pytest.approx(4.5)
    pending = df[df["num"] == 3].iloc[0]
    assert pending["score"] != pending["score"]  # NaN


def test_job_url_extracted_from_report_header(temp_root):
    df = tracker.load_applications()
    hsbc = df[df["num"] == 1].iloc[0]
    assert hsbc["job_url"] == "https://example.com/hsbc-dao"


def test_job_url_extracted_from_notes(temp_root):
    df = tracker.load_applications()
    jpm = df[df["num"] == 3].iloc[0]
    assert jpm["job_url"] == "https://example.com/jpm"


def test_status_counts_returns_dict(temp_root):
    df = tracker.load_applications()
    counts = tracker.status_counts(df)
    assert counts["Pending"] == 2
    assert counts["Evaluated"] == 1
    assert counts["Applied"] == 1
    assert counts["Discarded"] == 1


def test_update_status_rewrites_file(temp_root):
    tracker.update_status(3, "Applied")
    df = tracker.load_applications()
    assert df[df["num"] == 3].iloc[0]["status"] == "Applied"


def test_update_status_preserves_other_rows(temp_root):
    tracker.update_status(3, "Applied")
    df = tracker.load_applications()
    assert df[df["num"] == 1].iloc[0]["status"] == "Evaluated"
    assert df[df["num"] == 2].iloc[0]["status"] == "Applied"


def test_update_status_rejects_non_canonical(temp_root):
    with pytest.raises(ValueError):
        tracker.update_status(3, "Bogus")


def test_update_status_raises_for_missing_row(temp_root):
    with pytest.raises(KeyError):
        tracker.update_status(999, "Applied")


def test_canonical_statuses_includes_expected(temp_root):
    expected = {"Pending", "Evaluated", "Applied", "Interview", "Offer", "Rejected", "Discarded", "SKIP", "Watchlist"}
    assert expected.issubset(set(tracker.CANONICAL_STATUSES))


# ── Pipeline.md inbox helpers ──────────────────────────────────────────

def test_append_to_pipeline_creates_file(temp_root):
    p = tracker.append_to_pipeline("https://example.com/new-job-1", "FooCo", "Head of AI")
    body = p.read_text(encoding="utf-8")
    assert "## Pending" in body
    assert "- [ ] https://example.com/new-job-1" in body
    assert "FooCo" in body
    assert "Head of AI" in body


def test_append_to_pipeline_is_idempotent(temp_root):
    tracker.append_to_pipeline("https://example.com/dupe", "A", "B")
    tracker.append_to_pipeline("https://example.com/dupe", "A", "B")
    body = tracker.pipeline_path().read_text(encoding="utf-8")
    assert body.count("https://example.com/dupe") == 1


def test_append_to_pipeline_rejects_non_url(temp_root):
    with pytest.raises(ValueError):
        tracker.append_to_pipeline("just-some-text")


def test_read_pipeline_inbox_handles_missing(temp_root):
    # No pipeline.md yet in the fixture
    data = tracker.read_pipeline_inbox()
    assert data == {"pending": [], "processed": []}


def test_read_pipeline_inbox_parses_sections(temp_root):
    tracker.pipeline_path().write_text(
        "# Pipeline\n\n"
        "## Pending\n"
        "- [ ] https://a.example.com | FooCo | Head of AI\n"
        "- [!] https://b.example.com | Locked: login required\n"
        "\n## Processed\n"
        "- [x] #042 | https://c.example.com | BarCo | Dir DS | 4.1/5 | PDF ✅\n",
        encoding="utf-8",
    )
    data = tracker.read_pipeline_inbox()
    assert len(data["pending"]) == 2
    assert data["pending"][0]["url"] == "https://a.example.com"
    assert data["pending"][0]["company"] == "FooCo"
    assert data["pending"][0]["status"] == " "
    assert data["pending"][1]["status"] == "!"
    assert len(data["processed"]) == 1
    assert data["processed"][0]["url"] == "https://c.example.com"


def test_mark_pipeline_processed_moves_row(temp_root):
    tracker.append_to_pipeline("https://move.example.com", "MoveCo", "PM")
    assert tracker.mark_pipeline_processed("https://move.example.com")
    data = tracker.read_pipeline_inbox()
    assert all(e["url"] != "https://move.example.com" for e in data["pending"])
    assert any(e["url"] == "https://move.example.com" for e in data["processed"])


def test_mark_pipeline_processed_returns_false_for_unknown(temp_root):
    assert tracker.mark_pipeline_processed("https://never-added.example.com") is False


# ── promote_scanned_offers (scan → worklist) ──────────────────────────

def test_promote_adds_pending_rows_with_resolvable_url(temp_root):
    offers = [
        {"company": "Acme", "title": "Head of AI", "location": "Singapore",
         "url": "https://x.example.com/job1", "source": "workday-api"},
    ]
    res = tracker.promote_scanned_offers(offers)
    assert res["added"] == 1
    df = tracker.load_applications()
    row = df[df["company"] == "Acme"].iloc[0]
    assert row["status"] == "Pending"
    # URL stored in notes must resolve to job_url → makes the row evaluable.
    assert row["job_url"] == "https://x.example.com/job1"


def test_promote_dedupes_by_url_and_company_role(temp_root):
    offers = [
        {"company": "Acme", "title": "Head of AI", "url": "https://x.example.com/dup"},
        {"company": "Acme", "title": "Head of AI", "url": "https://x.example.com/dup"},   # dup URL
        # dup company+role vs fixture row 1 (HSBC / Head of DAO Singapore)
        {"company": "HSBC", "title": "Head of DAO Singapore", "url": "https://x.example.com/hsbc"},
        {"company": "Beta", "title": "Chief Data Officer", "url": "https://x.example.com/beta"},
    ]
    res = tracker.promote_scanned_offers(offers)
    assert res["added"] == 2          # Acme + Beta
    assert res["skipped"] == 2        # dup URL + dup company/role


def test_promote_skips_offers_missing_fields(temp_root):
    offers = [
        {"company": "", "title": "Head of AI", "url": "https://x.example.com/a"},
        {"company": "Acme", "title": "", "url": "https://x.example.com/b"},
        {"company": "Acme", "title": "Lead DS", "url": ""},
    ]
    res = tracker.promote_scanned_offers(offers)
    assert res["added"] == 0
    assert res["skipped"] == 3


def test_promote_sanitizes_pipe_in_company_role(temp_root):
    offers = [{"company": "A|B Corp", "title": "Head | of AI",
               "url": "https://x.example.com/pipe"}]
    res = tracker.promote_scanned_offers(offers)
    assert res["added"] == 1
    # Table must still parse — the row count grows by exactly one.
    df = tracker.load_applications()
    assert len(df) == 6
    assert df[df["job_url"] == "https://x.example.com/pipe"].iloc[0]["status"] == "Pending"


def test_promote_empty_is_noop(temp_root):
    before = len(tracker.load_applications())
    res = tracker.promote_scanned_offers([])
    assert res == {"added": 0, "skipped": 0, "nums": []}
    assert len(tracker.load_applications()) == before


def test_promote_sanitizes_pipe_in_url_keeps_table_valid(temp_root):
    # LLM (WebSearch) could return a URL with a pipe; it must not corrupt the row.
    offers = [{"company": "PipeCo", "title": "Head of AI",
               "url": "https://x.example.com/job?a=1|b=2"}]
    res = tracker.promote_scanned_offers(offers)
    assert res["added"] == 1
    df = tracker.load_applications()
    # Table still parses to exactly one new row, and the row is the PipeCo Pending.
    assert len(df) == 6
    row = df[df["company"] == "PipeCo"].iloc[0]
    assert row["status"] == "Pending"
    assert "|" not in row["notes"]
