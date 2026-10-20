from __future__ import annotations

from pathlib import Path
from typing import Any

import streamlit.components.v1 as components

_COMPONENT = components.declare_component(
    "rhodes_browser_profile_store",
    path=str(Path(__file__).resolve().parent),
)


def browser_profile_store(
    *,
    command: str,
    storage_key: str,
    payload: dict[str, Any] | None = None,
    nonce: int = 0,
    key: str | None = None,
):
    return _COMPONENT(
        command=str(command),
        storage_key=str(storage_key),
        payload=payload,
        nonce=int(nonce),
        default=None,
        key=key,
    )
