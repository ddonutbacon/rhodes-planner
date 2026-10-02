from __future__ import annotations
from urllib.parse import quote

# Community image repository. Images are loaded remotely and are never bundled.
BASE = "https://raw.githubusercontent.com/PuppiizSunniiz/Arknight-Images/main"
FALLBACK_BASE = "https://raw.githubusercontent.com/Aceship/Arknight-Images/main"


def operator_avatar_url(char_id: str) -> str:
    return f"{BASE}/avatars/{quote(char_id)}.png"


def operator_avatar_fallback_url(char_id: str) -> str:
    return f"{FALLBACK_BASE}/avatars/{quote(char_id)}.png"


def item_icon_url(item_id: str, item_meta: dict) -> str:
    icon_id = str(item_meta.get(item_id, {}).get("icon_id") or item_id)
    return f"{BASE}/items/{quote(icon_id)}.png"


def module_icon_url(module_id: str) -> str:
    return f"{BASE}/equip/icon/{quote(module_id)}.png"


def avatar_html(char_id: str, size: int = 96) -> str:
    primary = operator_avatar_url(char_id)
    fallback = operator_avatar_fallback_url(char_id)
    return (
        f'<img src="{primary}" width="{size}" height="{size}" '
        f'style="object-fit:contain;border-radius:12px;" '
        f'onerror="this.onerror=null;this.src=\'{fallback}\';">'
    )
