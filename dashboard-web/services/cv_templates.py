"""CV template registry helper.

Reads `templates/cv-templates.json` and exposes a list of `(slug, label, blurb)`
tuples for the review-page selectbox. Falls back to a one-entry list with the
classic template when the registry is missing or unreadable so the dashboard
stays usable on minimal installs.

Also renders a *visual* preview of any template filled with bundled example
data (`render_example_html`). The Role page embeds this in an inline iframe so
the user can see what each format looks like before generating — no `claude`
run, no PDF, just static HTML with fonts inlined as base64 so the preview's
typography matches the real PDF.
"""

from __future__ import annotations

import base64
import json
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Optional

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


# ── Visual preview ────────────────────────────────────────────────────────
#
# All five shipped templates share the SAME placeholder set and the SAME inner
# CSS class names (.job, .job-company, .competency-tag, .edu-item, …), so a
# single example-data fill renders correctly in every template — only the
# surrounding chrome (colors, fonts, columns) differs. The data below mirrors
# the bundled examples/cv-example.md (Alex Chen) so the preview is recognizable
# but obviously NOT the user's own CV.

_SAMPLE_FIELDS: Dict[str, str] = {
    "LANG": "en",
    "PAGE_WIDTH": "210mm",
    "NAME": "Alex Chen",
    "PHONE": "+1 (512) 555-0142",
    "EMAIL": "alex@example.com",
    "LINKEDIN_URL": "https://linkedin.com/in/alexchen",
    "LINKEDIN_DISPLAY": "linkedin.com/in/alexchen",
    "PORTFOLIO_URL": "https://alexchen.dev",
    "PORTFOLIO_DISPLAY": "alexchen.dev",
    "LOCATION": "Austin, TX — open to remote",
    "SECTION_SUMMARY": "Professional Summary",
    "SUMMARY_TEXT": (
        "Full-stack <strong>AI engineer</strong> with 6 years building production ML "
        "systems. Led the ML platform at a Series B fintech, scaling from 2 models to "
        "<strong>15+ in production</strong> — real-time fraud detection "
        "(<strong>99.7% precision</strong>, $2M/year saved), a recommendation engine "
        "(<strong>18% uplift</strong>), and an internal MLOps platform serving 4 teams."
    ),
    "SECTION_COMPETENCIES": "Core Competencies",
    "COMPETENCIES": "\n      ".join(
        f'<span class="competency-tag">{s}</span>'
        for s in (
            "ML Platform & MLOps",
            "Real-time Inference",
            "Fraud Detection",
            "Recommendation Systems",
            "LLM Applications",
            "Feature Stores",
            "Model Monitoring",
            "Team Leadership",
        )
    ),
    "SECTION_EXPERIENCE": "Work Experience",
    "EXPERIENCE": """
    <div class="job">
      <div class="job-header">
        <div>
          <span class="job-company">TechFin Corp</span>
          <span class="job-role"> &nbsp;·&nbsp; Senior ML Engineer / ML Platform Lead</span>
        </div>
        <span class="job-period">2020 – 2024 · Austin, TX</span>
      </div>
      <ul>
        <li>Led the <strong>ML platform team</strong> (3 engineers); built internal MLOps tooling — model registry, A/B testing framework, feature store.</li>
        <li>Designed a real-time <strong>fraud detection</strong> pipeline (Kafka → feature computation → inference → decision engine): <strong>99.7% precision at 50ms p99</strong>.</li>
        <li>Cut model deployment time from <strong>2 weeks to 4 hours</strong> with a CI/CD pipeline (GitHub Actions + SageMaker).</li>
      </ul>
    </div>

    <div class="job">
      <div class="job-header">
        <div>
          <span class="job-company">DataStartup Inc</span>
          <span class="job-role"> &nbsp;·&nbsp; ML Engineer</span>
        </div>
        <span class="job-period">2018 – 2020 · Remote</span>
      </div>
      <ul>
        <li>Built an NLP pipeline for document classification (BERT fine-tuning, <strong>94% accuracy</strong> on legal docs).</li>
        <li>Implemented search ranking with learning-to-rank models; set up experiment tracking with MLflow.</li>
      </ul>
    </div>
  """,
    "SECTION_PROJECTS": "Selected Projects",
    "PROJECTS": """
    <div class="project">
      <span class="project-title">FraudShield</span> <span class="project-badge">Open Source</span>
      <div class="project-desc">Real-time fraud detection framework — Kafka Streams + feature store + model serving. <strong>500+ GitHub stars</strong>.</div>
    </div>
    <div class="project">
      <span class="project-title">LLM Eval Toolkit</span> <span class="project-badge">Open Source</span>
      <div class="project-desc">Evaluation framework for LLM applications — custom metrics, regression testing, CI integration.</div>
    </div>
  """,
    "SECTION_EDUCATION": "Education",
    "EDUCATION": """
    <div class="edu-item">
      <div class="edu-header">
        <span class="edu-title">MS Computer Science — <span class="edu-org">UT Austin</span></span>
        <span class="edu-year">2018</span>
      </div>
    </div>
    <div class="edu-item">
      <div class="edu-header">
        <span class="edu-title">BS Computer Science — <span class="edu-org">UC Berkeley</span></span>
        <span class="edu-year">2016</span>
      </div>
    </div>
  """,
    "SECTION_CERTIFICATIONS": "",
    "CERTIFICATIONS": "",
    "SECTION_SKILLS": "Technical Stack",
    "SKILLS": """
    <div class="skills-grid">
      <div class="skill-item">PyTorch · TensorFlow · scikit-learn · Hugging Face · LangChain · SageMaker · MLflow · Kubeflow · Airflow · Kubernetes · Kafka · Redis · PostgreSQL · AWS · Python · Go · TypeScript · SQL.</div>
    </div>
  """,
}

_FONTS_DIR_NAME = "fonts"


@lru_cache(maxsize=1)
def _font_data_uris() -> Dict[str, str]:
    """Map each bundled font filename → a `data:font/woff2;base64,…` URI.

    Inlining lets the preview iframe (which has no access to the repo's
    ./fonts/ path) render with the real typeface. Returns an empty map if the
    fonts dir is absent — the preview then falls back to system fonts, which is
    fine for a thumbnail."""
    fonts_dir = project_root() / _FONTS_DIR_NAME
    out: Dict[str, str] = {}
    if not fonts_dir.is_dir():
        return out
    for f in fonts_dir.glob("*.woff2"):
        try:
            b64 = base64.b64encode(f.read_bytes()).decode("ascii")
            out[f.name] = f"data:font/woff2;base64,{b64}"
        except Exception:
            continue
    return out


def _inline_fonts(html: str) -> str:
    """Rewrite `url('./fonts/NAME.woff2')` references to inlined data URIs."""
    uris = _font_data_uris()
    if not uris:
        return html

    def _sub(m: "re.Match[str]") -> str:
        name = m.group("name")
        uri = uris.get(name)
        return f"url('{uri}')" if uri else m.group(0)

    return re.sub(r"url\(['\"]?\./fonts/(?P<name>[^'\")]+)['\"]?\)", _sub, html)


# Strips the empty Certifications block so the preview doesn't render a blank
# section (mirrors batch/build-cv-*.mjs). Tolerant of templates that omit the
# comment markers — then it's simply a no-op.
_CERT_BLOCK_RE = re.compile(
    r"<!-- CERTIFICATIONS -->\s*<div class=\"section[^\"]*\">[\s\S]*?</div>\s*(?=<!-- SKILLS -->)"
)


def render_example_html(slug: Optional[str]) -> Optional[str]:
    """Return the given template filled with bundled example data, fonts inlined.

    Returns None when the slug is unknown or the template file is missing, so
    the caller can show a graceful 'preview unavailable' note. This NEVER runs
    claude or touches the user's cv.md — it's purely a visual style preview."""
    tpl = get(slug)
    if tpl is None:
        return None
    path = project_root() / "templates" / tpl.file
    if not path.exists():
        return None
    try:
        html = path.read_text(encoding="utf-8")
    except Exception:
        return None

    for key, val in _SAMPLE_FIELDS.items():
        html = html.replace("{{" + key + "}}", val)
    html = _CERT_BLOCK_RE.sub("", html)
    html = _inline_fonts(html)
    return html
