from __future__ import annotations

from pathlib import Path


def app_root() -> Path:
    """Return the Rhodes Planner installation root independent of cwd/folder name."""
    return Path(__file__).resolve().parents[1]


def app_path(*parts: str) -> Path:
    """Build an absolute path inside the installation root."""
    return app_root().joinpath(*parts)
