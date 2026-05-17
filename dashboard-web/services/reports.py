"""reports/*.md parser.

Pulls header metadata (Score, Archetype, Legitimacy, URL, PDF, cover letter)
out of a single evaluation report. The body is rendered raw as Markdown by
the Streamlit page — we only structure the bits we need for filtering and
sidebar summaries.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional

from . import project_root


_HEADER_PATTERNS = {
    "date": re.compile(r"^\*\*Date:\*\*\s*(.+)$", re.MULTILINE),
    "archetype": re.compile(r"^\*\*Archetype:\*\*\s*(.+)$", re.MULTILINE),
    "score": re.compile(r"^\*\*Score:\*\*\s*(.+)$", re.MULTILINE),
    "legitimacy": re.compile(r"^\*\*Legitimacy:\*\*\s*(.+)$", re.MULTILINE),
    "url": re.compile(r"^\*\*URL:\*\*\s*(\S+)$", re.MULTILINE),
    "pdf": re.compile(r"^\*\*PDF:\*\*\s*(.+)$", re.MULTILINE),
    "cover_letter": re.compile(r"^\*\*Cover letter:\*\*\s*(.+)$", re.MULTILINE),
    "verification": re.compile(r"^\*\*Verification:\*\*\s*(.+)$", re.MULTILINE),
}

# Body-scan: posting date. Reports use a table row like
#   | **Posted** | 2026-04-27 (~3 weeks ago) |
# or a bolded line `**Posted:** 2026-04-27`. Some reports use prose ("~2026-02-26")
# instead of a clean date — we accept ~/≈ prefixes and grab the first YYYY-MM-DD.
_POSTED_PATTERNS = (
    re.compile(r"\*\*Posted(?:\s*/\s*Closes)?\*\*\s*(?:\||:)\s*[~≈]?\s*(\d{4}-\d{2}-\d{2})", re.IGNORECASE),
    re.compile(r"\*\*Date Posted\*\*\s*(?:\||:)\s*[~≈]?\s*(\d{4}-\d{2}-\d{2})", re.IGNORECASE),
    re.compile(r"\bPosted:?\s*[~≈]?\s*(\d{4}-\d{2}-\d{2})", re.IGNORECASE),
)

# Body-scan: salary / comp band. We try ordered patterns — the first hit wins.
# Examples seen across reports:
#   | **Compensation (posted)** | **USD $207,000 – $265,000** ...
#   | **Posted base range** | **USD $207,000 – $265,000** | ...
#   | **Posted range** | ... | SGD 20,000 – 24,000 / month
#   | **Posted comp range** | SGD 200,000 – 300,000 / annum
#   **Estimated total comp band:** **SGD 27–50K/m. ...**
#   **Estimated comp band for this role:** SGD 180–230K/yr total ...
_SALARY_PATTERNS = (
    re.compile(r"\*\*Compensation(?:\s*\(posted\))?\*\*\s*\|\s*\*{0,2}([^\n|*]+)", re.IGNORECASE),
    re.compile(r"\*\*Posted(?:\s+(?:base|comp))?\s+range\*\*\s*\|\s*\*{0,2}([^\n|*]+)", re.IGNORECASE),
    re.compile(r"\*\*Posted salary\s+\w+\*\*\s*\|[^|]*\|\s*\*{0,2}([^\n|*]+)", re.IGNORECASE),
    re.compile(r"\*\*(?:Salary|Comp|Compensation|Comp Band)[^:|*]*:\*\*\s*\*{0,2}([^\n|*]+)", re.IGNORECASE),
    re.compile(r"\*\*Estimated(?:\s+total)?\s+comp\s+band[^:]*:\*\*\s*\*{0,2}([^\n|*.]+)", re.IGNORECASE),
)


def _clean_salary(raw: str) -> str:
    s = raw.strip().strip("*").strip()
    # Drop trailing markdown table pipes / bold markers / stray punctuation.
    s = s.rstrip("|").strip().strip("*").strip().rstrip(",;:")
    if len(s) > 28:
        s = s[:27].rstrip() + "…"
    return s

_TLDR_TABLE = re.compile(r"\|\s*\*\*TL;DR\*\*\s*\|\s*([^|]+)\|")
_TLDR_LINE = re.compile(r"\*\*TL;DR:\*\*\s*(.+)")

# Accepts both English ("## A) Role Summary") and legacy Spanish
# ("## A) Resumen del Rol") section headers since reports may be in
# either language during the translation rollout.
_BLOCK_A_TO_C = re.compile(r"(^## A\).*?)(?=^## C\))", re.MULTILINE | re.DOTALL)
_BLOCK_F = re.compile(r"(^## F\).*?)(?=^## [A-Z]\))", re.MULTILINE | re.DOTALL)


@dataclass
class ReportSummary:
    path: str
    title: str
    date: str = ""
    archetype: str = ""
    score: str = ""
    legitimacy: str = ""
    url: str = ""
    pdf: str = ""
    cover_letter: str = ""
    verification: str = ""
    tldr: str = ""
    posted_date: str = ""
    salary_raw: str = ""

    def as_dict(self) -> dict:
        return asdict(self)


def parse_report(report_path: str | Path) -> Optional[ReportSummary]:
    path = Path(report_path)
    if not path.is_absolute():
        path = project_root() / path
    if not path.exists():
        return None

    text = path.read_text(encoding="utf-8", errors="ignore")
    lines = text.splitlines()
    title = lines[0].lstrip("# ").strip() if lines else path.stem

    header = text[:3000]
    summary = ReportSummary(path=str(path), title=title)
    for field, pattern in _HEADER_PATTERNS.items():
        if m := pattern.search(header):
            setattr(summary, field, m.group(1).strip())

    if t := _TLDR_TABLE.search(text):
        summary.tldr = t.group(1).strip()
    elif t := _TLDR_LINE.search(text):
        summary.tldr = t.group(1).strip()

    # Posted date — scan the full body (Block A is usually first 4-6KB).
    for pat in _POSTED_PATTERNS:
        if m := pat.search(text):
            summary.posted_date = m.group(1).strip()
            break

    # Salary — first matching pattern wins; trim & cap length for display.
    for pat in _SALARY_PATTERNS:
        if m := pat.search(text):
            cleaned = _clean_salary(m.group(1))
            if cleaned:
                summary.salary_raw = cleaned
                break

    return summary


def report_body(report_path: str | Path) -> str:
    path = Path(report_path)
    if not path.is_absolute():
        path = project_root() / path
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="ignore")


def extract_jd_section(report_path: str | Path) -> str:
    """Pull Block A + Block B (Role Summary + CV Match) from a report.
    These were captured by the worker from the JD itself — the closest
    structured JD content we have without re-fetching the URL."""
    body = report_body(report_path)
    if not body:
        return ""
    m = _BLOCK_A_TO_C.search(body)
    return m.group(1).rstrip() if m else ""


def extract_interview_section(report_path: str | Path) -> str:
    """Pull Block F (Interview Plan / Plan de Entrevistas) from a report."""
    body = report_body(report_path)
    if not body:
        return ""
    m = _BLOCK_F.search(body)
    return m.group(1).rstrip() if m else ""


def list_reports() -> list[ReportSummary]:
    reports_dir = project_root() / "reports"
    if not reports_dir.exists():
        return []
    out: list[ReportSummary] = []
    for f in sorted(reports_dir.glob("*.md")):
        if s := parse_report(f):
            out.append(s)
    return out
