from __future__ import annotations

from pathlib import Path
from typing import Any

import streamlit.components.v1 as components

_COMPONENT = components.declare_component(
    "rhodes_material_inventory",
    path=str(Path(__file__).resolve().parent),
)


def material_inventory(
    items: list[dict[str, Any]],
    *,
    columns: int = 6,
    placeholder: str = "Search inventory…",
    key: str | None = None,
):
    """
    Scrollable Arknights-style inventory editor.

    Returns the most recently edited item as:
        {"id": "<item id>", "quantity": <int>}
    """
    return _COMPONENT(
        items=items,
        columns=max(1, min(6, int(columns))),
        placeholder=str(placeholder),
        default=None,
        key=key,
    )
