from __future__ import annotations

from pathlib import Path
from typing import Any

import streamlit.components.v1 as components

_COMPONENT_DIR = Path(__file__).resolve().parent

_component = components.declare_component(
    "rhodes_operator_gallery",
    path=str(_COMPONENT_DIR),
)


def operator_gallery(
    operators: list[dict[str, Any]],
    *,
    selected_id: str | None = None,
    columns: int = 5,
    placeholder: str = "Search operator…",
    key: str | None = None,
):
    """Interactive visual operator picker with client-side live filtering."""
    return _component(
        operators=operators,
        selected_id=selected_id or "",
        columns=max(1, min(5, int(columns))),
        placeholder=placeholder,
        default=None,
        key=key,
    )
