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
