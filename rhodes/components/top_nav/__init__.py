from __future__ import annotations
from pathlib import Path
import streamlit.components.v1 as components

_COMPONENT = components.declare_component(
    "rhodes_top_nav",
    path=str(Path(__file__).resolve().parent),
)

def top_nav(items: list[str], *, selected: str, key: str | None = None):
    return _COMPONENT(
        items=items,
        selected=selected,
        default=selected,
        key=key,
    )
