"""applications.md parser + mutator.

Source of truth lives on disk. We parse the pipe-table, expose it as a
DataFrame, and write status updates back in place. New entries always go
through the TSV → merge-tracker.mjs path (per CLAUDE.md), never direct.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import pandas as pd

from . import project_root

CANONICAL_STATUSES = [
    "Pending",
    "Evaluated",
    "Applied",
    "Responded",
    "Interview",
    "Offer",
    "Rejected",
    "Discarded",
    "SKIP",
    "Watchlist",
]

_RE_REPORT_LINK = re.compile(r"\[(\d+)\]\(([^)]+)\)")
_RE_SCORE = re.compile(r"(\d+\.?\d*)/5")
_RE_REPORT_URL = re.compile(r"(?m)^\*\*URL:\*\*\s*(https?://\S+)")


@dataclass
class TrackerPaths:
    apps_file: Path
    reports_dir: Path
    pipeline_file: Path

    @classmethod
    def discover(cls) -> "TrackerPaths":
        root = project_root()
        apps = root / "data" / "applications.md"
        if not apps.exists():
            apps = root / "applications.md"
        return cls(
            apps_file=apps,
            reports_dir=root / "reports",
            pipeline_file=root / "data" / "pipeline.md",
        )


def _split_row(line: str) -> list[str]:
    """Split a markdown table row, tolerant of mixed pipe/tab formats."""
    line = line.strip()
    if "\t" in line:
        body = line.lstrip("|").strip()
        return [p.strip().strip("|") for p in body.split("\t")]
    body = line.strip("|")
    return [p.strip() for p in body.split("|")]


_RE_HTTP_URL = re.compile(r"https?://\S+")
_RE_ID_TOKEN = re.compile(r"\b(id\d{4,}|JR\d+|R-\d+|REF\d+|[a-f0-9]{16,})\b")
_RE_BARE_DOMAIN = re.compile(r"\b([a-z0-9-]+\.[a-z]{2,}(?:\.[a-z]{2,})?(?:/\S*)?)\b", re.IGNORECASE)


def _load_scan_history_urls():
    """Returns a list of URLs from scan-history.tsv. Cached at module level."""
    global _SCAN_URLS_CACHE
    try:
        return _SCAN_URLS_CACHE
    except NameError:
        pass
    paths = TrackerPaths.discover()
    hist = paths.apps_file.parent / "scan-history.tsv"
    urls: list[str] = []
    if hist.exists():
        for line in hist.read_text(encoding="utf-8", errors="ignore").splitlines()[1:]:
            cols = line.split("\t")
            if cols and cols[0].startswith("http"):
                urls.append(cols[0])
    globals()["_SCAN_URLS_CACHE"] = urls
    return urls


def _extract_url_from_notes(notes: str) -> Optional[str]:
    """Resolve a full URL from notes. Order:
       1. http(s)://... regex
       2. ID token (id12345, JR123, hex hash) matched against scan-history.tsv
       3. bare domain with path → prepend https://
       4. bare domain only → prepend https:// + www.
    """
    if not notes:
        return None
    if m := _RE_HTTP_URL.search(notes):
        return m.group(0).rstrip(".,;")

    # Try ID-based lookup against scan history.
    # If notes mention a specific job ID, the ONLY valid resolution is an
    # exact ID match — don't fall through to domain matching (would return
    # an unrelated job).
    history = _load_scan_history_urls()
    id_tokens = list(_RE_ID_TOKEN.finditer(notes))
    if id_tokens:
        for m in id_tokens:
            token = m.group(1)
            for url in history:
                if token in url:
                    return url
        return None  # ID was specified but not found — refuse to guess

    # Bare domain in notes (only reached when no ID token present)
    if m := _RE_BARE_DOMAIN.search(notes):
        candidate = m.group(1)
        # If notes already had a slug-ish path (e.g. sg.linkedin.com/jobs/view/4370154861)
        if "/" in candidate:
            return f"https://{candidate}"
        # If a bare domain, try scan-history first
        for url in history:
            if candidate in url:
                return url
        # Fallback: build a www. URL
        if not candidate.startswith("www."):
            candidate = f"www.{candidate}"
        return f"https://{candidate}"

    return None


def load_applications() -> pd.DataFrame:
    paths = TrackerPaths.discover()
    if not paths.apps_file.exists():
        return pd.DataFrame(
            columns=[
                "num", "date", "company", "role", "score", "status",
                "has_pdf", "report_path", "report_num", "notes", "job_url",
            ]
        )

    rows: list[dict] = []
    for raw in paths.apps_file.read_text(encoding="utf-8").splitlines():
        s = raw.strip()
        if not s or s.startswith("#") or s.startswith("|---") or s.startswith("| #"):
            continue
        if not s.startswith("|"):
            continue
        fields = _split_row(s)
        if len(fields) < 8:
            continue

        try:
            num = int(fields[0])
        except ValueError:
            continue

        score_raw = fields[4]
        score_match = _RE_SCORE.search(score_raw)
        score = float(score_match.group(1)) if score_match else None

        report_path, report_num = "", ""
        if rm := _RE_REPORT_LINK.search(fields[7]):
            report_num, report_path = rm.group(1), rm.group(2)

        notes = fields[8] if len(fields) > 8 else ""

        # job URL: prefer report header, fall back to notes
        job_url = _extract_url_from_notes(notes)
        if report_path:
            full = paths.reports_dir.parent / report_path
            if full.exists():
                head = full.read_text(encoding="utf-8", errors="ignore")[:1500]
                if u := _RE_REPORT_URL.search(head):
                    job_url = u.group(1)

        rows.append({
            "num": num,
            "date": fields[1],
            "company": fields[2],
            "role": fields[3],
            "score": score,
            "score_raw": score_raw,
            "status": fields[5],
            "has_pdf": "✅" in fields[6],
            "report_path": report_path,
            "report_num": report_num,
            "notes": notes,
            "job_url": job_url,
        })

    df = pd.DataFrame(rows)
    if not df.empty:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
    return df


def update_status(num: int, new_status: str, note_append: str = "") -> None:
    """Rewrite applications.md, replacing the status (and optionally
    appending a one-liner to notes) for the row with the given num.
    Preserves all whitespace and column formatting on other rows.
    """
    if new_status not in CANONICAL_STATUSES:
        raise ValueError(f"Status {new_status!r} is not canonical. See templates/states.yml")

    paths = TrackerPaths.discover()
    text = paths.apps_file.read_text(encoding="utf-8")
    new_lines: list[str] = []
    matched = False

    for raw in text.splitlines():
        s = raw.strip()
        if not s.startswith("|") or s.startswith("|---") or s.startswith("| #"):
            new_lines.append(raw)
            continue
        fields = _split_row(s)
        if len(fields) < 8:
            new_lines.append(raw)
            continue
        try:
            row_num = int(fields[0])
        except ValueError:
            new_lines.append(raw)
            continue

        if row_num != num:
            new_lines.append(raw)
            continue

        fields[5] = new_status
        if note_append:
            existing = fields[8] if len(fields) > 8 else ""
            fields[8] = (existing + " " + note_append).strip() if existing else note_append
        if len(fields) <= 8 and note_append:
            fields.append(note_append)

        new_lines.append("| " + " | ".join(fields) + " |")
        matched = True

    if not matched:
        raise KeyError(f"No tracker row with num={num}")

    paths.apps_file.write_text("\n".join(new_lines) + "\n", encoding="utf-8")


def status_counts(df: pd.DataFrame) -> dict[str, int]:
    if df.empty:
        return {}
    return df["status"].value_counts().to_dict()
