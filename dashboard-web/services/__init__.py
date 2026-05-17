"""Service layer for the Streamlit career-ops dashboard.

Thin wrappers over the existing .mjs scripts and on-disk markdown.
The Streamlit pages must never read or mutate files directly — they
go through this package so the data contract from CLAUDE.md is preserved.
"""

from pathlib import Path


def project_root() -> Path:
    return Path(__file__).resolve().parent.parent.parent
