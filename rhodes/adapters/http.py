from __future__ import annotations

import json
import os
import time
from pathlib import Path

import requests
from platformdirs import user_cache_dir

from rhodes import __version__

CACHE_DIR = Path(user_cache_dir("RhodesPlanner", "RhodesPlanner"))
UA = f"RhodesPlanner/{__version__} (+portfolio project; non-commercial)"


def _ensure_cache_dir() -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)


def _read_cached_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        # A partial/corrupt cache must never brick the application.
        try:
            path.unlink(missing_ok=True)
        except OSError:
            pass
        return None


def _write_cached_json(path: Path, data) -> None:
    _ensure_cache_dir()
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    os.replace(temp, path)


def get_json(url: str, cache_key: str, max_age_hours: int = 24):
    _ensure_cache_dir()
    path = CACHE_DIR / f"{cache_key}.json"

    if path.exists():
        try:
            age = time.time() - path.stat().st_mtime
        except OSError:
            age = max_age_hours * 3600 + 1
        if age <= max_age_hours * 3600:
            cached = _read_cached_json(path)
            if cached is not None:
                return cached

    r = requests.get(url, timeout=60, headers={"User-Agent": UA})
    r.raise_for_status()
    data = r.json()
    try:
        _write_cached_json(path, data)
    except OSError:
        # Cache is optional. A read-only profile/cache location should not block use.
        pass
    return data


def clear_cache():
    if not CACHE_DIR.exists():
        return
    for p in CACHE_DIR.glob("*.json"):
        try:
            p.unlink(missing_ok=True)
        except OSError:
            pass
