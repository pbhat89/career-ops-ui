"""CV template registry helper.

Reads `templates/cv-templates.json` and exposes a list of `(slug, label, blurb)`
tuples for the review-page selectbox. Falls back to a one-entry list with the
classic template when the registry is missing or unreadable so the dashboard
stays usable on minimal installs.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from . import project_root


@dataclass(frozen=True)
class CvTemplate:
    slug: str
    label: str
    file: str
    blurb: str = ""


_FALLBACK = (
    CvTemplate(
        slug="classic",
        label="ATS Classic",
        file="cv-template.html",
        blurb="Single-column DM Sans + Space Grotesk. Original ATS-optimized layout.",
    ),
)


def _registry_path() -> Path:
    return project_root() / "templates" / "cv-templates.json"


def list_templates() -> List[CvTemplate]:
    path = _registry_path()
    if not path.exists():
        return list(_FALLBACK)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return list(_FALLBACK)
    raw = payload.get("templates") if isinstance(payload, dict) else None
    if not isinstance(raw, list) or not raw:
        return list(_FALLBACK)

    out: List[CvTemplate] = []
    for entry in raw:
        if not isinstance(entry, dict):
            continue
        slug = str(entry.get("slug") or "").strip()
        label = str(entry.get("label") or "").strip()
        file = str(entry.get("file") or "").strip()
        if not slug or not label or not file:
            continue
        out.append(CvTemplate(
            slug=slug,
            label=label,
            file=file,
            blurb=str(entry.get("blurb") or "").strip(),
        ))
    return out or list(_FALLBACK)


def default_slug() -> str:
    path = _registry_path()
    if not path.exists():
        return "classic"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return "classic"
    slug = payload.get("default") if isinstance(payload, dict) else None
    return str(slug).strip() if slug else "classic"


def get(slug: Optional[str]) -> Optional[CvTemplate]:
    if not slug:
        return None
    for tpl in list_templates():
        if tpl.slug == slug:
            return tpl
    return None
