from __future__ import annotations
import json
import time
from pathlib import Path
import requests
from platformdirs import user_cache_dir

CACHE_DIR = Path(user_cache_dir("rhodes-planner", "RhodesPlanner"))
CACHE_DIR.mkdir(parents=True, exist_ok=True)

UA = "RhodesPlanner/0.1 (+portfolio project; non-commercial)"


def get_json(url: str, cache_key: str, max_age_hours: int = 24):
    path = CACHE_DIR / f"{cache_key}.json"

    if path.exists():
        age = time.time() - path.stat().st_mtime
        if age <= max_age_hours * 3600:
            return json.loads(path.read_text(encoding="utf-8"))

    r = requests.get(url, timeout=60, headers={"User-Agent": UA})
    r.raise_for_status()
    data = r.json()
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return data


def clear_cache():
    for p in CACHE_DIR.glob("*.json"):
        p.unlink(missing_ok=True)
