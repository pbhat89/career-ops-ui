"""Service layer for the Streamlit career-ops dashboard.

Thin wrappers over the existing .mjs scripts and on-disk markdown.
The Streamlit pages must never read or mutate files directly — they
go through this package so the data contract from CLAUDE.md is preserved.
"""

import os
from pathlib import Path


def project_root() -> Path:
    # CAREEROPS_PROJECT_ROOT lets a worktree / detached checkout point at the
    # canonical data dir (cv.md, config/, data/, reports/) so reviewers see live
    # state instead of an empty first-run shell.
    override = os.environ.get("CAREEROPS_PROJECT_ROOT", "").strip()
    if override:
        p = Path(override).expanduser().resolve()
        if p.is_dir():
            return p
    return Path(__file__).resolve().parent.parent.parent
