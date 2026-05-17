"""Per-role Interest tracker (Yes/No/blank).

Keyed by tracker `num` (not company) so two different evaluations of the same
employer stay independent — the user explicitly wanted "saved only for those
roles at the time and not the company."

Storage: `data/interest.tsv` with columns: num\tinterest\tupdated_at.
Read on every render (cheap — usually <100 rows). Writes are full-rewrite
since the file is tiny.
"""

from __future__ import annotations

import datetime as _dt
from pathlib import Path

from . import project_root

_HEADER = "num\tinterest\tupdated_at\n"
_VALID = {"", "Yes", "No"}


def _path() -> Path:
    return project_root() / "data" / "interest.tsv"


def _ensure_file() -> Path:
    p = _path()
    p.parent.mkdir(parents=True, exist_ok=True)
    if not p.exists():
        p.write_text(_HEADER, encoding="utf-8")
    return p


def load_interest() -> dict[int, str]:
    """Return {num: interest} for every row in the TSV. Missing/blank → ''."""
    p = _path()
    if not p.exists():
        return {}
    out: dict[int, str] = {}
    for line in p.read_text(encoding="utf-8").splitlines()[1:]:
        if not line.strip():
            continue
        parts = line.split("\t")
        if len(parts) < 2:
            continue
        try:
            num = int(parts[0])
        except ValueError:
            continue
        out[num] = parts[1].strip()
    return out


def set_interest(num: int, value: str) -> None:
    """Set interest for a single row. value ∈ {'', 'Yes', 'No'}."""
    if value not in _VALID:
        raise ValueError(f"interest must be one of {_VALID}, got {value!r}")
    _ensure_file()
    rows = load_interest()
    rows[int(num)] = value
    ts = _dt.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    out = [_HEADER.rstrip()]
    for n in sorted(rows):
        v = rows[n]
        out.append(f"{n}\t{v}\t{ts if n == int(num) else ''}")
    _path().write_text("\n".join(out) + "\n", encoding="utf-8")
