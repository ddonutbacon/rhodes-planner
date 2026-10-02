from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict

from platformdirs import user_data_dir

DATA_DIR = Path(user_data_dir("RhodesPlanner", "RhodesPlanner"))
PROFILE_PATH = DATA_DIR / "profile.json"


def profile_path() -> Path:
    return PROFILE_PATH


def load_profile() -> Dict[str, Any]:
    if not PROFILE_PATH.exists():
        return {}
    try:
        data = json.loads(PROFILE_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def save_profile(payload: Dict[str, Any]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    temp = PROFILE_PATH.with_suffix(".tmp")
    temp.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    os.replace(temp, PROFILE_PATH)


def clear_profile() -> None:
    PROFILE_PATH.unlink(missing_ok=True)
