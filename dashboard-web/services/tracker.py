"""applications.md parser + mutator.

Source of truth lives on disk. We parse the pipe-table, expose it as a
DataFrame, and write status updates back in place. New entries always go
through the TSV → merge-tracker.mjs path (per CLAUDE.md), never direct.
"""

from __future__ import annotations

import datetime as dt
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


def _norm_url(u: str) -> str:
    return str(u or "").strip().rstrip("/").lower()


def _norm_text(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", str(s or "").lower())


def _cell(s: str) -> str:
    """Sanitize a value for a markdown table cell: no pipes, no newlines."""
    return str(s or "").replace("|", "/").replace("\n", " ").replace("\r", " ").strip()


def promote_scanned_offers(offers: list[dict]) -> dict:
    """Append freshly-scanned offers to applications.md as `Pending` rows so
    they appear in the main worklist and can be evaluated from the UI.

    Each offer is a dict with keys company / title / location / url / source
    (the shape `scan.mjs --json` emits). The JD URL is stored in the Notes
    column as `URL: <url>` — that's where `load_applications()` resolves
    `job_url`, which is what makes the row evaluable.

    Idempotent: skips any offer whose URL already exists in the tracker, and
    any whose company+role already has a row. Returns
    {added, skipped, nums: [...]}.
    """
    result = {"added": 0, "skipped": 0, "nums": []}
    if not offers:
        return result

    paths = TrackerPaths.discover()
    if not paths.apps_file.exists():
        return result

    df = load_applications()
    seen_urls = set()
    seen_company_role = set()
    max_num = 0
    if not df.empty:
        for _, r in df.iterrows():
            if r.get("job_url"):
                seen_urls.add(_norm_url(r["job_url"]))
            seen_company_role.add((_norm_text(r.get("company")), _norm_text(r.get("role"))))
            try:
                max_num = max(max_num, int(r["num"]))
            except (TypeError, ValueError):
                pass

    today = dt.date.today().isoformat()
    new_rows: list[str] = []
    for o in offers:
        url = str(o.get("url") or "").strip()
        company = _cell(o.get("company"))
        role = _cell(o.get("title"))
        if not url or not company or not role:
            result["skipped"] += 1
            continue
        nurl = _norm_url(url)
        cr = (_norm_text(company), _norm_text(role))
        if nurl in seen_urls or cr in seen_company_role:
            result["skipped"] += 1
            continue
        seen_urls.add(nurl)
        seen_company_role.add(cr)
        max_num += 1
        note_bits = [f"URL: {url}"]
        loc = _cell(o.get("location"))
        if loc:
            note_bits.append(f"({loc})")
        note = " ".join(note_bits)
        new_rows.append(
            f"| {max_num} | {today} | {company} | {role} | -/5 | Pending | ❌ | - | {note} |"
        )
        result["added"] += 1
        result["nums"].append(max_num)

    if not new_rows:
        return result

    # Insert directly after the header separator row (|---|...), so the freshly
    # scanned jobs surface at the TOP of the tracker — newest first.
    lines = paths.apps_file.read_text(encoding="utf-8").splitlines()
    insert_idx = None
    for i, ln in enumerate(lines):
        s = ln.strip()
        if s.startswith("|") and set(s) <= set("|-: "):
            insert_idx = i + 1
            break
    if insert_idx is None:
        # No separator found — append at end of file.
        lines.extend(new_rows)
    else:
        lines[insert_idx:insert_idx] = new_rows
    paths.apps_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return result


def status_counts(df: pd.DataFrame) -> dict[str, int]:
    if df.empty:
        return {}
    return df["status"].value_counts().to_dict()


# ── Pipeline.md helpers (the /career-ops pipeline "inbox") ────────────


def pipeline_path() -> Path:
    return project_root() / "data" / "pipeline.md"


def append_to_pipeline(url: str, company: str = "", role: str = "") -> Path:
    """Append `- [ ] URL | Company | Role` to the `## Pending` section of
    data/pipeline.md. Creates the file with a stub if it doesn't exist.
    Idempotent against the URL — won't add a duplicate row.
    """
    p = pipeline_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    url = url.strip()
    if not url.startswith("http"):
        raise ValueError(f"Not a URL: {url!r}")

    body = ""
    if p.exists():
        body = p.read_text(encoding="utf-8")
        if url in body:
            return p  # already present — skip silently

    line_parts = [f"- [ ] {url}"]
    if company.strip():
        line_parts.append(company.strip())
    if role.strip():
        line_parts.append(role.strip())
    new_line = " | ".join(line_parts)

    if not body:
        body = (
            "# Pipeline — Inbox\n\n"
            "## Pending\n"
            f"{new_line}\n\n"
            "## Processed\n"
        )
        p.write_text(body, encoding="utf-8")
        return p

    if "## Pending" in body:
        # Insert immediately after the Pending header
        body = re.sub(
            r"(## Pending\s*\n)",
            r"\1" + new_line + "\n",
            body, count=1,
        )
    else:
        body = body.rstrip() + f"\n\n## Pending\n{new_line}\n"
    p.write_text(body, encoding="utf-8")
    return p


def read_pipeline_inbox() -> dict:
    """Parse data/pipeline.md and return {pending: [...], processed: [...]}.
    Each entry is a dict with keys: raw, url, company, role, status (' '|'!'|'x').
    """
    p = pipeline_path()
    if not p.exists():
        return {"pending": [], "processed": []}

    pending: list[dict] = []
    processed: list[dict] = []
    section = None
    for raw in p.read_text(encoding="utf-8", errors="ignore").splitlines():
        s = raw.strip()
        if s.startswith("## Pending"):
            section = "pending"; continue
        if s.startswith("## Processed"):
            section = "processed"; continue
        if not s.startswith("- ["):
            continue
        m = re.match(r"-\s*\[(.)\]\s*(.*)", s)
        if not m:
            continue
        flag, rest = m.group(1), m.group(2).strip()
        parts = [p.strip() for p in rest.split("|")]
        url = next((p for p in parts if p.startswith("http")), "")
        non_url = [p for p in parts if not p.startswith("http") and not p.startswith("#")]
        entry = {
            "raw": raw,
            "url": url,
            "company": non_url[0] if non_url else "",
            "role":    non_url[1] if len(non_url) > 1 else "",
            "status":  flag,
        }
        if section == "processed":
            processed.append(entry)
        else:
            pending.append(entry)
    return {"pending": pending, "processed": processed}


def mark_pipeline_processed(url: str) -> bool:
    """Find `- [ ] {url} ...` in pipeline.md, rewrite as `- [x] {url} ...`,
    move to the Processed section. Returns True if a change was made."""
    p = pipeline_path()
    if not p.exists():
        return False
    body = p.read_text(encoding="utf-8")
    pattern = re.compile(rf"^-\s*\[ \](\s+{re.escape(url)}.*)$", re.MULTILINE)
    m = pattern.search(body)
    if not m:
        return False
    old_line = m.group(0)
    new_line = f"- [x]{m.group(1)}"
    body = body.replace(old_line, "")
    # Drop empty Pending lines that may result.
    body = re.sub(r"\n{3,}", "\n\n", body)
    # Append to Processed section
    if "## Processed" in body:
        body = re.sub(
            r"(## Processed\s*\n)",
            r"\1" + new_line + "\n",
            body, count=1,
        )
    else:
        body = body.rstrip() + f"\n\n## Processed\n{new_line}\n"
    p.write_text(body, encoding="utf-8")
    return True
