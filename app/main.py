from __future__ import annotations

import html
import os
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from rhodes import __version__ as package_version
from rhodes.adapters.arkprts_export import parse_arkprts_full_export
from rhodes.adapters.assets import avatar_html, item_icon_url, operator_avatar_url
from rhodes.adapters.gamedata import (
    advancement_item_ids,
    build_item_metadata_map,
    build_operator_cost_model,
    fetch_game_data,
    leveling_cost,
    module_catalog_for_operator,
    operator_catalog,
    phase_max_level,
)
from rhodes.adapters.http import clear_cache
from rhodes.adapters.penguin import fetch_penguin_matrix, normalize_stages
from rhodes.adapters.penguin_export import build_penguin_planner_config_json
from rhodes.components.browser_store import browser_profile_store
from rhodes.components.operator_gallery import operator_gallery
from rhodes.components.material_inventory import material_inventory
from rhodes.components.top_nav import top_nav
from rhodes.core.crafting import (
    add_dualchip_factory_recipes,
    expand_high_tier_farm_targets,
    parse_workshop_recipes,
    simulate_crafting,
)
from rhodes.core.farming import best_stage_for_item, build_farming_plan
from rhodes.core.models import (
    CostBundle,
    Inventory,
    ModuleProgress,
    OperatorState,
    SkillState,
    StageModel,
    UpgradeGoal,
)
from rhodes.core.planner import aggregate_costs, calculate_upgrade_cost
from rhodes.core.profile_store import (
    clear_profile,
    load_profile,
    profile_path,
    save_profile,
)
from rhodes.core.v080 import (
    active_goal_pairs,
    diff_import,
    merge_import_preserving_manual,
    move_list_item,
    normalised_snapshot,
    plan_signature,
    resolve_special_acquisitions,
    spendable_inventory,
)

__version__ = "0.8.0"
EXP_VALUES = {"2001": 200, "2002": 400, "2003": 1000, "2004": 2000}
EXP_CARD_NAMES = {
    "2001": "T1 Drill Battle Record",
    "2002": "T2 Frontline Battle Record",
    "2003": "T3 Tactical Battle Record",
    "2004": "T4 Strategic Battle Record",
}
AUXILIARY_INVENTORY_IDS = {"4006"}  # Purchase Certificate

MATERIAL_DISPLAY_ORDER = [
    "LMD",
    "Purchase Certificate",
    "Strategic Battle Record",
    "Tactical Battle Record",
    "Frontline Battle Record",
    "Drill Battle Record",
    "Skill Summary - 3",
    "Skill Summary - 2",
    "Skill Summary - 1",
    "Module Data Block",
    "Data Supplement Instrument",
    "Data Supplement Stick",
    "Rephasic Enantiomer",
    "Nucleic Crystal Sinter",
    "Crystalline Electronic Unit",
    "D32 Steel",
    "Bipolar Nanoflake",
    "Polymerization Preparation",
    "Energy Aggregation Motor Unit",
    "Electron Unit",
    "Liquefied Ether Adsorbent",
    "Liquefied High-Energy Gas",
    "Chiral Refractor",
    "Coagulative Nodule",
    "Cyclocene Prefab",
    "Aggregate Cyclocene",
    "Solidified Fiber Board",
    "Fuscous Fiber",
    "Transmuted Salt Agglomerate",
    "Transmuted Salt",
    "Cutting Fluid Solution",
    "Compound Cutting Fluid",
    "Refined Solvent",
    "Semi-Synthetic Solvent",
    "Crystalline Circuit",
    "Crystalline Component",
    "Incandescent Alloy Block",
    "Incandescent Alloy",
    "Polymerized Gel",
    "Coagulating Gel",
    "White Horse Kohl",
    "Loxic Kohl",
    "Manganese Trihydrate",
    "Manganese Ore",
    "Grindstone Pentahydrate",
    "Grindstone",
    "RMA70-24",
    "RMA70-12",
    "Orirock Concentration",
    "Orirock Cluster",
    "Orirock Cube",
    "Orirock",
    "Optimized Device",
    "Integrated Device",
    "Device",
    "Damaged Device",
    "Polyester Lump",
    "Polyester Pack",
    "Polyester",
    "Ester",
    "Sugar Lump",
    "Sugar Pack",
    "Sugar",
    "Sugar Substitute",
    "Oriron Block",
    "Oriron Cluster",
    "Oriron",
    "Oriron Shard",
    "Keton Colloid",
    "Aketon",
    "Polyketon",
    "Diketon",
    "Chip Catalyst",
    "Vanguard Dualchip",
    "Guard Dualchip",
    "Defender Dualchip",
    "Sniper Dualchip",
    "Caster Dualchip",
    "Medic Dualchip",
    "Supporter Dualchip",
    "Specialist Dualchip",
    "Vanguard Chip Pack",
    "Guard Chip Pack",
    "Defender Chip Pack",
    "Sniper Chip Pack",
    "Caster Chip Pack",
    "Medic Chip Pack",
    "Supporter Chip Pack",
    "Specialist Chip Pack",
    "Vanguard Chip",
    "Guard Chip",
    "Defender Chip",
    "Sniper Chip",
    "Caster Chip",
    "Medic Chip",
    "Supporter Chip",
    "Specialist Chip",
]
PROFILE_BACKEND = os.environ.get("RHODES_PROFILE_BACKEND", "browser").strip().lower()
if PROFILE_BACKEND not in {"browser", "file"}:
    PROFILE_BACKEND = "browser"

st.set_page_config(
    page_title="Rhodes Planner",
    page_icon="🧭",
    layout="wide",
)

st.markdown(
    """
<style>
.block-container {max-width: 1320px; padding-top: 1.25rem;}
div[data-testid="stMetric"] {
  border:1px solid rgba(128,128,128,.22); padding:10px 12px; border-radius:12px;
}
.operator-card {
  display:flex; gap:16px; align-items:center; border:1px solid rgba(128,128,128,.20);
  border-radius:14px; padding:12px 14px; margin:6px 0 12px 0;
}
.operator-title {font-size:1.2rem;font-weight:700;}
.operator-sub {opacity:.72;}
.fast-note {
  border-left:4px solid #2f80ed; padding:8px 12px; margin:8px 0 14px 0;
  background:rgba(47,128,237,.07);
}
.compact-row {padding:3px 0;}
</style>
""",
    unsafe_allow_html=True,
)


# ---------------------------
# Data loading and state
# ---------------------------
def load_sample():
    return json.loads((ROOT / "rhodes/data/sample.json").read_text(encoding="utf-8"))


@st.cache_data(show_spinner=False)
def get_live_data(server: str):
    t0 = time.perf_counter()
    (
        chars, items, constants, modules, stage_table, building,
        en_chars, en_items, en_modules, en_stage_table,
    ) = fetch_game_data()

    penguin_error = None
    try:
        matrix = fetch_penguin_matrix(server)
        stage_source = stage_table if server == "CN" else en_stage_table
        stages = normalize_stages(matrix, stage_source)
    except Exception as exc:
        stages = []
        penguin_error = str(exc)

    return (
        chars, items, constants, modules, building,
        en_chars, en_items, en_modules,
        [x.model_dump() for x in stages],
        penguin_error,
        time.perf_counter() - t0,
    )


def get_data(mode: str, server: str):
    if mode == "Live":
        (
            chars, items, constants, modules, building,
            en_chars, en_items, en_modules,
            stage_dicts, penguin_error, cold_seconds,
        ) = get_live_data(server)
        return (
            chars, items, constants, modules, building,
            en_chars, en_items, en_modules,
            [StageModel.model_validate(x) for x in stage_dicts],
            False, penguin_error, cold_seconds,
        )

    sample = load_sample()
    return (
        sample["characters"], sample["items"], sample["constants"],
        sample["modules"], {}, sample["characters"], sample["items"],
        sample["modules"],
        [StageModel.model_validate(x) for x in sample["stages"]],
        True, None, 0.0,
    )


def exp_from_cards(inv: Inventory) -> int:
    return sum(int(inv.exp_cards.get(iid, 0) or 0) * value for iid, value in EXP_VALUES.items())


def _hydrate_state(saved: dict | None):
    saved = saved if isinstance(saved, dict) else {}

    try:
        inventory = Inventory.model_validate(saved.get("inventory", {}))
    except Exception:
        inventory = Inventory()

    operators = {}
    for cid, raw in (saved.get("operators") or {}).items():
        try:
            operators[str(cid)] = OperatorState.model_validate(raw)
        except Exception:
            continue

    settings = saved.get("settings") or {}
    st.session_state.inventory = inventory
    st.session_state.operators = operators
    st.session_state.goals = list(saved.get("goals") or [])
    st.session_state.costs = list(saved.get("costs") or [])

    if saved.get("reserve_qty"):
        st.session_state.reserve_qty = {
            str(k): max(0.0, float(v or 0))
            for k, v in (saved.get("reserve_qty") or {}).items()
        }
    else:
        # v0.7 compatibility: old reserve set meant reserve all currently owned.
        st.session_state.reserve_qty = {
            str(iid): float(inventory.materials.get(str(iid), 0) or 0)
            for iid in (saved.get("reserved_materials") or [])
        }

    st.session_state.reserve_lmd = max(0, int(settings.get("reserve_lmd", 0) or 0))
    st.session_state.reserve_exp = max(0, int(settings.get("reserve_exp", 0) or 0))
    st.session_state.planning_days = float(settings.get("planning_days", 7.0) or 0)
    st.session_state.base_lmd_per_day = int(settings.get("base_lmd_per_day", 0) or 0)
    st.session_state.base_t3_per_day = int(settings.get("base_t3_per_day", 0) or 0)
    st.session_state.default_e2_level = int(settings.get("default_e2_level", 60) or 60)
    st.session_state.import_snapshot = saved.get("import_snapshot") or {}
    st.session_state.import_audit = saved.get("import_audit") or {}
    st.session_state.performance = {}
    st.session_state.editing_goal_id = None
    st.session_state.deleted_goal = None
    st.session_state.gallery_epoch = 0
    st.session_state.top_page = st.session_state.get("top_page", "Home")
    st.session_state._v080_loaded = True


def profile_payload() -> dict:
    return {
        "schema_version": 8,
        "rhodes_version": __version__,
        "inventory": st.session_state.inventory.model_dump(),
        "operators": {
            cid: op.model_dump()
            for cid, op in st.session_state.operators.items()
        },
        "goals": st.session_state.goals,
        "costs": st.session_state.costs,
        "reserve_qty": {
            str(iid): float(qty)
            for iid, qty in st.session_state.reserve_qty.items()
            if float(qty or 0) > 0
        },
        "settings": {
            "reserve_lmd": int(st.session_state.reserve_lmd),
            "reserve_exp": int(st.session_state.reserve_exp),
            "planning_days": float(st.session_state.planning_days),
            "base_lmd_per_day": int(st.session_state.base_lmd_per_day),
            "base_t3_per_day": int(st.session_state.base_t3_per_day),
            "default_e2_level": int(st.session_state.default_e2_level),
        },
        "import_snapshot": st.session_state.import_snapshot,
        "import_audit": st.session_state.import_audit,
    }


def ensure_state():
    if st.session_state.get("_v080_loaded"):
        return

    if PROFILE_BACKEND == "file":
        _hydrate_state(load_profile())
        return

    # Public/web mode: profile lives in this browser only, not on the Streamlit server.
    result = browser_profile_store(
        command="load",
        storage_key="rhodes_planner_profile_v080",
        nonce=0,
        key="rhodes_profile_loader",
    )

    if isinstance(result, dict) and result.get("status") == "loaded":
        _hydrate_state(result.get("profile") or {})
        st.rerun()

    if isinstance(result, dict) and result.get("status") == "error":
        _hydrate_state({})
        st.session_state._browser_storage_warning = str(
            result.get("message") or "Browser storage is unavailable."
        )
        st.rerun()

    st.title("🧭 Rhodes Planner")
    st.caption("Loading your browser-local Rhodes profile…")
    st.stop()


def persist_profile():
    payload = profile_payload()

    if PROFILE_BACKEND == "file":
        save_profile(payload)
        return

    st.session_state._browser_save_payload = payload
    st.session_state._browser_save_epoch = int(
        st.session_state.get("_browser_save_epoch", 0)
    ) + 1


def flush_browser_profile_save():
    if PROFILE_BACKEND != "browser":
        return

    payload = st.session_state.pop("_browser_save_payload", None)
    if payload is None:
        return

    epoch = int(st.session_state.get("_browser_save_epoch", 0))
    browser_profile_store(
        command="save",
        storage_key="rhodes_planner_profile_v080",
        payload=payload,
        nonce=epoch,
        key=f"rhodes_profile_writer_{epoch}",
    )


def reset_profile_state():
    _hydrate_state({})
    st.session_state.goals = []
    st.session_state.costs = []
    st.session_state.reserve_qty = {}
    st.session_state.reserve_lmd = 0
    st.session_state.reserve_exp = 0
    st.session_state.import_snapshot = {}
    st.session_state.import_audit = {}
    persist_profile()


def clipboard_button(text: str, *, label: str = "Copy Penguin Statistics config"):
    payload = json.dumps(str(text))
    components.html(
        f"""
        <div style="font-family:system-ui,sans-serif;">
          <button id="copyBtn" style="
            border:1px solid #4b5563;background:#1f4f8f;color:#fff;
            padding:9px 14px;border-radius:8px;cursor:pointer;font-size:14px;font-weight:600;">
            📋 {html.escape(label)}
          </button>
          <span id="copyStatus" style="margin-left:9px;font-size:13px;color:#9ca3af;"></span>
        </div>
        <script>
          const payload = {payload};
          const btn = document.getElementById("copyBtn");
          const status = document.getElementById("copyStatus");
          btn.addEventListener("click", async () => {{
            try {{
              if (navigator.clipboard && window.isSecureContext) {{
                await navigator.clipboard.writeText(payload);
              }} else {{
                const area = document.createElement("textarea");
                area.value = payload;
                area.style.position = "fixed";
                area.style.opacity = "0";
                document.body.appendChild(area);
                area.focus();
                area.select();
                document.execCommand("copy");
                document.body.removeChild(area);
              }}
              status.textContent = "Copied ✓";
              setTimeout(() => status.textContent = "", 1800);
            }} catch (err) {{
              status.textContent = "Copy failed";
            }}
          }});
        </script>
        """,
        height=46,
    )



SUBCLASS_ALIASES = {
    "pioneer": "Pioneer",
    "charger": "Charger",
    "bearer": "Standard Bearer",
    "tactician": "Tactician",
    "agent": "Agent",
    "fighter": "Brawler",
    "fearless": "Dreadnought",
    "artsfghter": "Arts Fighter",
    "instructor": "Instructor",
    "lord": "Lord",
    "sword": "Swordmaster",
    "musha": "Musha",
    "reaper": "Reaper",
    "centurion": "Centurion",
    "crusher": "Crusher",
    "liberator": "Liberator",
    "artsprotector": "Arts Protector",
    "fortress": "Fortress",
    "duelist": "Duelist",
    "juggernaut": "Juggernaut",
    "guardian": "Guardian",
    "protector": "Protector",
    "sentinel": "Sentinel Protector",
    "fastshot": "Marksman",
    "aoesniper": "Artilleryman",
    "siegesniper": "Besieger",
    "spreadshooter": "Spreadshooter",
    "closeRange": "Heavyshooter",
    "longrange": "Deadeye",
    "bombarder": "Flinger",
    "corecaster": "Core Caster",
    "splashcaster": "Splash Caster",
    "chaincaster": "Chain Caster",
    "mystic": "Mystic Caster",
    "phalanx": "Phalanx Caster",
    "drone": "Mech-Accord Caster",
    "blastcaster": "Blast Caster",
    "medic": "Medic",
    "therapist": "Therapist",
    "wandermedic": "Wandering Medic",
    "incantationmedic": "Incantation Medic",
    "ringhealer": "Multi-target Medic",
    "slow": "Decel Binder",
    "summon": "Summoner",
    "bard": "Bard",
    "craftsman": "Artificer",
    "ritualist": "Ritualist",
    "executor": "Executor",
    "merchant": "Merchant",
    "trapper": "Trapmaster",
    "dollkeeper": "Dollkeeper",
    "ambusher": "Ambusher",
    "hookmaster": "Hookmaster",
    "pusher": "Push Stroker",
    "geek": "Geek",
}


def subclass_label(raw: str | None) -> str:
    raw = str(raw or "").strip()
    if not raw:
        return "Unknown"
    if raw in SUBCLASS_ALIASES:
        return SUBCLASS_ALIASES[raw]
    # Conservative fallback: show the canonical ID rather than guessing a lore/archetype name.
    return raw.replace("_", " ").replace("-", " ").title()


def build_gallery_rows(catalog: dict, *, owned_only: bool = False) -> list[dict]:
    rows = []
    for cid, meta in catalog.items():
        owned = cid in st.session_state.operators
        if owned_only and not owned:
            continue
        raw_char = chars.get(cid, {}) if isinstance(chars, dict) else {}
        subclass_id = str((raw_char or {}).get("subProfessionId") or "")
        rows.append({
            "id": cid,
            "name": meta.get("name", cid),
            "rarity": int(meta.get("rarity", 0)),
            "owned": owned,
            "availability": meta.get("availability", "EN"),
            "class_name": meta.get("class", ""),
            "subclass_id": subclass_id,
            "subclass_name": subclass_label(subclass_id),
            "image": operator_avatar_url(cid),
            "search": " ".join([
                str(meta.get("name", "")),
                str(meta.get("cn_name", "")),
                str(cid),
                str(meta.get("class", "")),
                subclass_id,
                subclass_label(subclass_id),
            ]),
        })
    rows.sort(key=lambda r: (0 if r["owned"] else 1, -r["rarity"], str(r["name"]).casefold()))
    return rows


def get_existing_state(cid: str, catalog: dict) -> OperatorState:
    meta = catalog[cid]
    return st.session_state.operators.get(
        cid,
        OperatorState(operator_id=cid, name=meta["name"], rarity=meta["rarity"]),
    ).model_copy(deep=True)


def render_operator_header(cid: str, catalog: dict, note: str):
    meta = catalog[cid]
    st.markdown(
        f"""
        <div class="operator-card">
          {avatar_html(cid, 78)}
          <div>
            <div class="operator-title">{html.escape(str(meta["name"]))}</div>
            <div class="operator-sub">
              {"★" * int(meta["rarity"])} · {html.escape(str(meta.get("class", "")))} ·
              {html.escape(str(meta.get("availability", "EN")))}
            </div>
            <div class="operator-sub">{html.escape(note)}</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )




def _normalise_inventory_name(value: str) -> str:
    return "".join(ch for ch in str(value).casefold() if ch.isalnum())


_MATERIAL_ORDER_INDEX = {
    _normalise_inventory_name(name): index
    for index, name in enumerate(MATERIAL_DISPLAY_ORDER)
}


def inventory_display_sort_key(iid: str) -> tuple[int, str]:
    if iid == "4001":
        name = "LMD"
    elif iid in EXP_CARD_NAMES:
        # Drop explicit tier prefix here so it matches the in-game item name order.
        name = EXP_CARD_NAMES[iid].split(" ", 1)[1]
    else:
        name = item_names.get(iid, iid)

    normalised = _normalise_inventory_name(name)
    return (
        _MATERIAL_ORDER_INDEX.get(normalised, 10_000),
        str(name).casefold(),
    )


def inventory_card_payload(iid: str) -> dict:
    if iid == "4001":
        quantity = int(st.session_state.inventory.lmd)
        name = "LMD"
    elif iid in EXP_CARD_NAMES:
        quantity = int(st.session_state.inventory.exp_cards.get(iid, 0) or 0)
        name = EXP_CARD_NAMES[iid].split(" ", 1)[1]
    else:
        quantity = int(st.session_state.inventory.materials.get(iid, 0) or 0)
        name = item_names.get(iid, iid)

    return {
        "id": str(iid),
        "name": str(name),
        "image": item_icon_url(str(iid), item_meta),
        "quantity": quantity,
        "search": " ".join([
            str(name),
            str(item_meta.get(str(iid), {}).get("cn_name") or ""),
            str(iid),
        ]),
    }


def apply_inventory_card_change(change: dict | None) -> bool:
    if not isinstance(change, dict):
        return False

    iid = str(change.get("id") or "")
    if not iid:
        return False

    try:
        quantity = max(0, int(change.get("quantity", 0) or 0))
    except (TypeError, ValueError):
        return False

    inv = st.session_state.inventory.model_copy(deep=True)

    if iid == "4001":
        if int(inv.lmd) == quantity:
            return False
        inv.lmd = quantity
    elif iid in EXP_VALUES:
        old = int(inv.exp_cards.get(iid, 0) or 0)
        if old == quantity:
            return False
        inv.exp_cards[iid] = quantity
        inv.materials[iid] = quantity
        inv.exp = exp_from_cards(inv)
    else:
        old = int(inv.materials.get(iid, 0) or 0)
        if old == quantity:
            return False
        inv.materials[iid] = quantity

    st.session_state.inventory = inv
    persist_profile()
    return True


def stage_by_code(code: str):
    return next((s for s in stages if s.code == code), None)


def exp_stage_output(stage, runs: int) -> tuple[str, str, str]:
    if stage is None:
        return ("EXP from Battle Records (tier unavailable)", item_icon_url("2003", item_meta), "EXP tier mix unavailable")

    parts = []
    highest_id = "2003"
    for iid in ("2004", "2003", "2002", "2001"):
        drop = next((d for d in stage.drops if d.item_id == iid and d.expected_per_run > 0), None)
        if drop:
            highest_id = iid if not parts else highest_id
            expected_cards = float(drop.expected_per_run) * int(runs)
            parts.append(f"{expected_cards:,.1f} × {EXP_CARD_NAMES[iid]}")

    if parts:
        title = " + ".join(EXP_CARD_NAMES[iid] for iid in ("2004","2003","2002","2001")
                           if any(d.item_id == iid and d.expected_per_run > 0 for d in stage.drops))
        return (title, item_icon_url(highest_id, item_meta), " · ".join(parts))

    return (
        "EXP (Battle Records; tier mix unavailable)",
        item_icon_url("2003", item_meta),
        f"{stage.exp_per_run * runs:,.0f} EXP",
    )


def farming_line_display(row, acquisition_notes: list[dict] | None = None) -> dict:
    purpose = str(row.purpose)
    note = ""

    if purpose == "LMD":
        material_name = "LMD"
        material_icon = item_icon_url("4001", item_meta)
        expected_text = f"{row.expected_output:,.0f} LMD"
    elif purpose == "EXP":
        stage = stage_by_code(row.stage_code)
        material_name, material_icon, expected_text = exp_stage_output(stage, row.runs)
    else:
        material_name = item_names.get(purpose, purpose)
        material_icon = item_icon_url(purpose, item_meta)
        expected_text = f"{row.expected_output:,.2f}".rstrip("0").rstrip(".")

    for entry in acquisition_notes or []:
        if str(entry.get("farm_item_id")) == purpose:
            note = str(entry.get("summary") or "")
            break

    return {
        "Stage": row.stage_code,
        "Icon": material_icon,
        "Material / Resource": material_name,
        "Runs": row.runs,
        "Sanity": row.sanity,
        "Expected": expected_text,
        "Why": note,
    }


def mark_performance(name: str, seconds: float):
    st.session_state.performance[name] = round(float(seconds) * 1000, 1)


def clear_planner_selection():
    st.session_state.planner_selected_cid = None
    st.session_state.gallery_epoch += 1


ensure_state()
flush_browser_profile_save()

# ---------------------------
# Sidebar and public data
# ---------------------------
with st.sidebar:
    st.header("Data & Settings")
    mode = st.radio("Public data", ["Live", "Offline demo"], index=0)
    server = st.selectbox("Farming server", ["US", "JP", "KR", "CN"], index=0)

    st.divider()
    st.markdown("**Planning defaults**")
    default_e2_level = st.number_input(
        "Default E2 target level",
        min_value=1, max_value=90,
        value=int(st.session_state.default_e2_level),
        step=10,
    )
    if int(default_e2_level) != int(st.session_state.default_e2_level):
        st.session_state.default_e2_level = int(default_e2_level)
        persist_profile()

    st.divider()
    if st.button("Refresh public data"):
        clear_cache()
        st.cache_data.clear()
        st.rerun()

    if PROFILE_BACKEND == "browser":
        st.caption("Profile: saved in this browser.")
    else:
        st.caption("Profile: saved locally for this offline test.")

    if st.button("Clear saved profile"):
        if PROFILE_BACKEND == "file":
            clear_profile()
        reset_profile_state()
        st.rerun()

t_data = time.perf_counter()
try:
    (
        chars, items, constants, modules, building,
        en_chars, en_items, en_modules, stages,
        is_demo, penguin_error, cold_data_seconds,
    ) = get_data(mode, server)
except Exception as exc:
    st.error("Live public-data load failed. Falling back to offline demo.")
    st.code(str(exc))
    (
        chars, items, constants, modules, building,
        en_chars, en_items, en_modules, stages,
        is_demo, penguin_error, cold_data_seconds,
    ) = get_data("Offline demo", server)
mark_performance("page data access", time.perf_counter() - t_data)
if cold_data_seconds:
    mark_performance("cold public-data load", cold_data_seconds)

t_catalog = time.perf_counter()
catalog = operator_catalog(chars, en_chars)
item_meta = build_item_metadata_map(items, en_items)
en_item_meta = build_item_metadata_map(en_items)
item_names = {iid: meta["name"] for iid, meta in item_meta.items()}
advancement_ids = advancement_item_ids(chars, modules, item_meta)
recipes = add_dualchip_factory_recipes(parse_workshop_recipes(building), item_meta)
mark_performance("catalogue preparation", time.perf_counter() - t_catalog)

for cid, op in st.session_state.operators.items():
    if cid in catalog:
        op.name = catalog[cid]["name"]
        op.rarity = catalog[cid]["rarity"]
for goal in st.session_state.goals:
    cid = str(goal.get("operator_id") or "")
    if cid in catalog:
        goal["operator"] = catalog[cid]["name"]
    goal.setdefault("active", True)

st.title("🧭 Rhodes Planner")
st.caption(f"Account-aware Arknights progression, crafting and farming planner · v{__version__}")

page = top_nav(
    ["Home", "Account", "Planner", "Farming"],
    selected=st.session_state.get("top_page", "Home"),
    key="rhodes_top_nav",
)
if page:
    st.session_state.top_page = page
else:
    page = st.session_state.get("top_page", "Home")
if st.session_state.get("_browser_storage_warning"):
    st.warning(
        "Browser profile storage is unavailable in this browser session. "
        "Rhodes will still work, but use Account → Rhodes profile backup to export your progress."
    )

if is_demo:
    st.warning("Offline demo data is active.")
elif penguin_error:
    st.warning(f"Penguin farming data unavailable: {penguin_error}")


# ---------------------------
# Home
# ---------------------------
if page == "Home":
    inv = st.session_state.inventory
    active_count = sum(1 for g in st.session_state.goals if g.get("active", True))
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Operators", f"{len(st.session_state.operators):,}")
    c2.metric("Active goals", f"{active_count:,}")
    c3.metric("LMD", f"{inv.lmd:,}")
    c4.metric("EXP stock · T3 Tactical equiv.", f"{inv.exp/1000:,.1f}")

    st.markdown("### What Rhodes Planner does")
    st.write(
        "Rhodes Planner helps you work out what you actually need to build your "
        "Arknights operators, based on what you already own."
    )
    st.markdown(
        "- Track operators, materials, LMD and Battle Records.\n"
        "- Plan multiple operator upgrades together.\n"
        "- Account for reserves, crafting, shop acquisition routes and passive RIIC production.\n"
        "- Get a final farming checklist with material names, stages, runs and sanity."
    )


# ---------------------------
# Account
# ---------------------------
elif page == "Account":
    st.subheader("Account")
    st.caption("ArkPRTS is now a refresh source. You can also maintain the profile manually.")

    with st.expander("Rhodes profile backup / transfer"):
        st.caption(
            "Your normalised Rhodes profile contains planner state, not game credentials. "
            "Use this to move the profile between browsers/devices."
        )
        st.download_button(
            "Download Rhodes profile",
            data=json.dumps(profile_payload(), ensure_ascii=False, indent=2),
            file_name="rhodes_profile_v080.json",
            mime="application/json",
        )
        profile_file = st.file_uploader(
            "Import a Rhodes profile",
            type=["json"],
            key="rhodes_profile_import",
        )
        if profile_file is not None and st.button("Load Rhodes profile"):
            try:
                loaded = json.load(profile_file)
                if not isinstance(loaded, dict):
                    raise ValueError("Profile root must be a JSON object.")
                _hydrate_state(loaded)
                persist_profile()
                st.success("Rhodes profile loaded.")
                st.rerun()
            except Exception as exc:
                st.error(f"Profile import failed: {exc}")


    ark_file = st.file_uploader("ArkPRTS full data export (.json)", type=["json"], key="full_proto_import")

    if ark_file is not None and st.button("Analyse import", type="primary"):
        try:
            if getattr(ark_file, "size", 0) > 25 * 1024 * 1024:
                raise ValueError("ArkPRTS export exceeds the 25 MB limit.")
            t0 = time.perf_counter()
            payload = json.load(ark_file)
            raw_status = payload.get("status") if isinstance(payload, dict) else {}
            raw_lmd = int((raw_status or {}).get("gold", 0) or 0)

            imported_inv, imported_ops, meta = parse_arkprts_full_export(payload)
            parsed_lmd = int(imported_inv.lmd)
            del payload

            allowed = set(advancement_ids) | set(EXP_VALUES) | AUXILIARY_INVENTORY_IDS
            imported_inv.materials = {
                str(iid): qty for iid, qty in imported_inv.materials.items()
                if str(iid) in allowed
            }
            imported_inv.exp_cards = {
                iid: int(imported_inv.materials.get(iid, imported_inv.exp_cards.get(iid, 0)) or 0)
                for iid in EXP_VALUES
            }
            imported_inv.exp = exp_from_cards(imported_inv)

            for cid, op in imported_ops.items():
                if cid in catalog:
                    op.name = catalog[cid]["name"]
                    op.rarity = catalog[cid]["rarity"]

            st.session_state.pending_import = {
                "inventory": imported_inv.model_dump(),
                "operators": {cid: op.model_dump() for cid, op in imported_ops.items()},
                "metadata": meta,
                "raw_lmd": raw_lmd,
                "parsed_lmd": parsed_lmd,
                "analysed_at": datetime.now(timezone.utc).isoformat(),
                "diff": diff_import(
                    st.session_state.inventory,
                    st.session_state.operators,
                    imported_inv,
                    imported_ops,
                ),
            }
            mark_performance("ArkPRTS parse", time.perf_counter() - t0)
            st.success("Import analysed. Review the verification and diff below before applying it.")
        except Exception as exc:
            st.error(f"Import analysis failed: {exc}")

    pending = st.session_state.get("pending_import")
    if pending:
        st.markdown("### Import verification")
        v1, v2, v3, v4 = st.columns(4)
        v1.metric("Raw JSON status.gold", f'{int(pending["raw_lmd"]):,}')
        v2.metric("Rhodes parsed LMD", f'{int(pending["parsed_lmd"]):,}')
        v3.metric("Operators", f'{len(pending["operators"]):,}')
        v4.metric("Inventory entries", f'{int(pending["metadata"].get("inventory_entry_count", 0)):,}')
        if int(pending["raw_lmd"]) == int(pending["parsed_lmd"]):
            st.success("LMD parser audit passed: raw JSON and normalised LMD match exactly.")
        else:
            st.error("LMD parser audit failed: the raw JSON and normalised LMD differ.")

        d = pending["diff"]
        st.markdown("### Changes versus editable account")
        d1, d2, d3, d4 = st.columns(4)
        d1.metric("LMD", f'{d["lmd_before"]:,} → {d["lmd_after"]:,}')
        d2.metric("Changed operators", d["changed_operators"])
        d3.metric("New operators", d["added_operators"])
        d4.metric("Changed materials", d["changed_materials"])

        merge_mode = st.radio(
            "When applying this import",
            ["Use import as the new editable account", "Preserve manual overrides since the previous import"],
            horizontal=True,
        )
        a1, a2 = st.columns(2)
        if a1.button("Apply import", type="primary"):
            imported_inv = Inventory.model_validate(pending["inventory"])
            imported_ops = {
                cid: OperatorState.model_validate(raw)
                for cid, raw in pending["operators"].items()
            }
            merge_info = {}
            if merge_mode.startswith("Preserve"):
                imported_inv, imported_ops, merge_info = merge_import_preserving_manual(
                    current_inventory=st.session_state.inventory,
                    current_operators=st.session_state.operators,
                    previous_snapshot=st.session_state.import_snapshot,
                    imported_inventory=imported_inv,
                    imported_operators=imported_ops,
                )
                imported_inv.exp = exp_from_cards(imported_inv)

            st.session_state.inventory = imported_inv
            st.session_state.operators = imported_ops
            st.session_state.import_snapshot = normalised_snapshot(
                Inventory.model_validate(pending["inventory"]),
                {
                    cid: OperatorState.model_validate(raw)
                    for cid, raw in pending["operators"].items()
                },
                pending["metadata"],
            )
            st.session_state.import_audit = {
                "raw_status_gold": int(pending["raw_lmd"]),
                "parsed_lmd": int(pending["parsed_lmd"]),
                "applied_at": datetime.now(timezone.utc).isoformat(),
                "merge_info": merge_info,
            }
            st.session_state.pending_import = None
            persist_profile()
            st.success("Account refreshed. Saved planning goals were preserved.")
            st.rerun()

        if a2.button("Discard analysed import"):
            st.session_state.pending_import = None
            st.rerun()

    st.divider()
    st.markdown("### Manual operator state")
    owned_only = st.toggle("Owned operators only", value=False, key="account_owned_only")
    account_selected = operator_gallery(
        build_gallery_rows(catalog, owned_only=owned_only),
        selected_id=st.session_state.get("account_selected_cid"),
        columns=5,
        placeholder="Type an operator name…",
        key=f"account_gallery_{st.session_state.gallery_epoch}",
    )
    if account_selected and account_selected in catalog:
        st.session_state.account_selected_cid = account_selected
        cid = account_selected
        existing = get_existing_state(cid, catalog)
        meta = catalog[cid]
        render_operator_header(
            cid, catalog,
            "Editable account state" if cid in st.session_state.operators else "Not currently in editable account",
        )

        with st.form(f"account_operator_form_{cid}"):
            e1, e2, e3, e4 = st.columns(4)
            elite = e1.selectbox("Elite", [0, 1, 2], index=existing.elite)
            max_lvl = phase_max_level(constants, meta["rarity"], elite)
            level = e2.number_input("Level", min_value=1, max_value=max_lvl, value=min(existing.level, max_lvl), step=1)
            skill = e3.selectbox("Skill rank", list(range(1, 8)), index=max(0, existing.skill_level - 1))
            potential = e4.selectbox("Potential", list(range(1, 7)), index=min(5, existing.potential_rank))

            m1, m2, m3 = st.columns(3)
            s1 = m1.selectbox("S1 mastery", [0, 1, 2, 3], index=existing.mastery.s1)
            s2 = m2.selectbox("S2 mastery", [0, 1, 2, 3], index=existing.mastery.s2)
            s3 = m3.selectbox("S3 mastery", [0, 1, 2, 3], index=existing.mastery.s3)

            module_defs = module_catalog_for_operator(modules, cid, en_modules)
            module_levels = {}
            if module_defs:
                st.caption("Modules")
                cols = st.columns(min(3, len(module_defs)))
                for idx, (mid, mdef) in enumerate(module_defs.items()):
                    old = existing.modules.get(mid, ModuleProgress()).level
                    module_levels[mid] = cols[idx % len(cols)].selectbox(
                        str(mdef["name"]).strip("'\""),
                        [0, 1, 2, 3],
                        index=old,
                    )

            save_op = st.form_submit_button("Save operator state", type="primary")

        if save_op:
            module_states = {mid: state.model_copy(deep=True) for mid, state in existing.modules.items()}
            for mid, lvl in module_levels.items():
                module_states[mid] = ModuleProgress(level=int(lvl), locked=(int(lvl) == 0))
            st.session_state.operators[cid] = OperatorState(
                operator_id=cid,
                name=meta["name"],
                rarity=meta["rarity"],
                elite=int(elite),
                level=int(level),
                skill_level=int(skill),
                mastery=SkillState(s1=int(s1), s2=int(s2), s3=int(s3)),
                modules=module_states,
                potential_rank=int(potential) - 1,
            )
            persist_profile()
            st.success(f'Saved {meta["name"]}.')

    st.divider()
    st.markdown("### Inventory")
    st.caption(
        "Edit your account inventory directly. Items follow the in-game depot order "
        "from left to right, then top to bottom."
    )

    inventory_ids = set(advancement_ids) | AUXILIARY_INVENTORY_IDS | set(EXP_VALUES) | {"4001"}
    ordered_inventory_ids = sorted(
        inventory_ids,
        key=inventory_display_sort_key,
    )

    inventory_items = [
        inventory_card_payload(iid)
        for iid in ordered_inventory_ids
    ]

    inventory_change = material_inventory(
        inventory_items,
        columns=6,
        placeholder="Search inventory…",
        key="account_material_inventory",
    )

    if apply_inventory_card_change(inventory_change):
        st.toast("Inventory updated.", icon="✓")
        st.rerun()


# ---------------------------
# Planner
# ---------------------------
elif page == "Planner":
    st.subheader("Upgrade Planner")
    st.caption("Choose → set target → save. Starting state is editable only when you need it.")

    # Compact current plan
    if st.session_state.goals:
        st.markdown("### Current plan")
        active_total = sum(1 for g in st.session_state.goals if g.get("active", True))
        st.caption(f"{active_total} active · {len(st.session_state.goals)-active_total} paused")

        b1, b2, b3 = st.columns([1, 1, 4])
        if b1.button("Activate all"):
            for g in st.session_state.goals:
                g["active"] = True
            persist_profile()
            st.rerun()
        if b2.button("Pause all"):
            for g in st.session_state.goals:
                g["active"] = False
            persist_profile()
            st.rerun()

        for idx, goal in enumerate(st.session_state.goals):
            current = goal["current"]
            target = goal["target"]
            active_now = bool(goal.get("active", True))
            cols = st.columns([1.0, 2.7, 4.3, .55, .55, .8, .55])
            new_active = cols[0].toggle("Active", value=active_now, key=f"active_goal_{idx}_{goal['operator_id']}")
            if new_active != active_now:
                goal["active"] = bool(new_active)
                persist_profile()

            cols[1].markdown(f'**{goal["operator"]}**')
            mod = f' · Mod{target["module_level"]}' if target.get("module_id") else ""
            cols[2].caption(
                f'E{current["elite"]} Lv{current["level"]} → E{target["elite"]} Lv{target["level"]} · '
                f'SL{target["skill_level"]} · M{target["mastery"]["s1"]}/M{target["mastery"]["s2"]}/M{target["mastery"]["s3"]}{mod}'
                + ("" if new_active else " · paused")
            )
            if cols[3].button("↑", key=f"up_{idx}", disabled=(idx == 0)):
                st.session_state.goals = move_list_item(st.session_state.goals, idx, -1)
                st.session_state.costs = move_list_item(st.session_state.costs, idx, -1)
                persist_profile()
                st.rerun()
            if cols[4].button("↓", key=f"down_{idx}", disabled=(idx == len(st.session_state.goals)-1)):
                st.session_state.goals = move_list_item(st.session_state.goals, idx, 1)
                st.session_state.costs = move_list_item(st.session_state.costs, idx, 1)
                persist_profile()
                st.rerun()
            if cols[5].button("Edit", key=f"edit_{idx}"):
                st.session_state.editing_goal_id = goal["operator_id"]
                st.rerun()
            if cols[6].button("×", key=f"delete_{idx}"):
                st.session_state.deleted_goal = {
                    "goal": st.session_state.goals.pop(idx),
                    "cost": st.session_state.costs.pop(idx),
                    "index": idx,
                }
                persist_profile()
                st.rerun()

        if st.session_state.deleted_goal:
            deleted = st.session_state.deleted_goal
            u1, u2 = st.columns([1, 5])
            if u1.button("Undo delete"):
                idx = int(deleted["index"])
                st.session_state.goals.insert(idx, deleted["goal"])
                st.session_state.costs.insert(idx, deleted["cost"])
                st.session_state.deleted_goal = None
                persist_profile()
                st.rerun()
            u2.caption(f'Removed {deleted["goal"]["operator"]}.')
        st.divider()

    editing_goal = next(
        (g for g in st.session_state.goals if g.get("operator_id") == st.session_state.get("editing_goal_id")),
        None,
    )

    if editing_goal:
        cid = editing_goal["operator_id"]
        st.info(f'Editing **{editing_goal["operator"]}**')
        if st.button("Cancel edit"):
            st.session_state.editing_goal_id = None
            st.rerun()
    else:
        st.markdown("### Choose operator")
        owned_only = st.toggle("Owned only", value=False, key="planner_owned_only")
        selected = operator_gallery(
            build_gallery_rows(catalog, owned_only=owned_only),
            selected_id=st.session_state.get("planner_selected_cid"),
            columns=5,
            placeholder="Start typing an operator name…",
            key=f"planner_gallery_{st.session_state.gallery_epoch}",
        )
        if selected and selected in catalog:
            st.session_state.planner_selected_cid = selected
        cid = st.session_state.get("planner_selected_cid")

    if cid and cid in catalog:
        meta = catalog[cid]
        rarity = int(meta["rarity"])

        if editing_goal:
            starting = OperatorState.model_validate(editing_goal["current"])
            saved_target = editing_goal["target"]
        else:
            starting = get_existing_state(cid, catalog)
            saved_target = {}

        source = "Editable account baseline" if cid in st.session_state.operators else "Manual planning baseline · E0 Lv1"
        render_operator_header(cid, catalog, source)

        # Starting state is compact by default.
        st.markdown("### Starting state")
        st.caption(
            f'E{starting.elite} Lv{starting.level} · SL{starting.skill_level} · '
            f'S1 M{starting.mastery.s1} / S2 M{starting.mastery.s2} / S3 M{starting.mastery.s3}'
        )
        edit_start = st.toggle("Edit starting state for this goal", value=False, key=f"edit_start_{cid}")

        start_state = starting.model_copy(deep=True)
        if edit_start:
            s1c, s2c, s3c = st.columns(3)
            start_elite = s1c.selectbox("Start Elite", [0,1,2], index=starting.elite, key=f"start_e_{cid}")
            start_max = phase_max_level(constants, rarity, start_elite)
            start_level = s2c.number_input("Start level", min_value=1, max_value=start_max, value=min(starting.level, start_max), step=1, key=f"start_l_{cid}_{start_elite}")
            start_skill = s3c.selectbox("Start skill", list(range(1,8)), index=max(0, starting.skill_level-1), key=f"start_sl_{cid}")
            sm1, sm2, sm3 = st.columns(3)
            ss1 = sm1.selectbox("Start S1", [0,1,2,3], index=starting.mastery.s1, key=f"start_s1_{cid}")
            ss2 = sm2.selectbox("Start S2", [0,1,2,3], index=starting.mastery.s2, key=f"start_s2_{cid}")
            ss3 = sm3.selectbox("Start S3", [0,1,2,3], index=starting.mastery.s3, key=f"start_s3_{cid}")
            start_state.elite = int(start_elite)
            start_state.level = int(start_level)
            start_state.skill_level = int(start_skill)
            start_state.mastery = SkillState(s1=int(ss1), s2=int(ss2), s3=int(ss3))

            if st.button("Save this starting state to Account", key=f"save_start_account_{cid}"):
                saved = start_state.model_copy(deep=True)
                saved.name = meta["name"]
                saved.rarity = rarity
                st.session_state.operators[cid] = saved
                persist_profile()
                st.success("Editable account baseline updated.")

        st.markdown("### Target")
        last_goal = st.session_state.goals[-1] if st.session_state.goals else None
        preset_options = ["E2 default / SL7", "E2 max / SL7", "Custom"]
        if last_goal and last_goal.get("operator_id") != cid:
            preset_options.insert(2, "Reuse previous target pattern")
        preset = st.radio("Target preset", preset_options, horizontal=True, key=f"preset_{cid}")

        if preset == "E2 default / SL7":
            target_elite_default = max(start_state.elite, 2)
            target_level_default = max(
                start_state.level if start_state.elite == 2 else 1,
                min(phase_max_level(constants, rarity, 2), int(st.session_state.default_e2_level)),
            )
            target_skill_default = max(start_state.skill_level, 7)
            mastery_defaults = {
                "s1": start_state.mastery.s1,
                "s2": start_state.mastery.s2,
                "s3": start_state.mastery.s3,
            }
        elif preset == "E2 max / SL7":
            target_elite_default = max(start_state.elite, 2)
            target_level_default = phase_max_level(constants, rarity, 2)
            target_skill_default = max(start_state.skill_level, 7)
            mastery_defaults = {
                "s1": start_state.mastery.s1,
                "s2": start_state.mastery.s2,
                "s3": start_state.mastery.s3,
            }
        elif preset == "Reuse previous target pattern" and last_goal:
            pt = last_goal["target"]
            target_elite_default = max(start_state.elite, int(pt.get("elite", 2)))
            max_for_e = phase_max_level(constants, rarity, target_elite_default)
            target_level_default = min(max_for_e, max(
                start_state.level if start_state.elite == target_elite_default else 1,
                int(pt.get("level", 60)),
            ))
            target_skill_default = max(start_state.skill_level, int(pt.get("skill_level", 7)))
            pm = pt.get("mastery") or {}
            mastery_defaults = {
                "s1": max(start_state.mastery.s1, int(pm.get("s1", 0))),
                "s2": max(start_state.mastery.s2, int(pm.get("s2", 0))),
                "s3": max(start_state.mastery.s3, int(pm.get("s3", 0))),
            }
        else:
            target_elite_default = max(start_state.elite, int(saved_target.get("elite", start_state.elite)))
            max_for_e = phase_max_level(constants, rarity, target_elite_default)
            target_level_default = min(max_for_e, max(
                start_state.level if start_state.elite == target_elite_default else 1,
                int(saved_target.get("level", start_state.level)),
            ))
            target_skill_default = max(start_state.skill_level, int(saved_target.get("skill_level", start_state.skill_level)))
            pm = saved_target.get("mastery") or {}
            mastery_defaults = {
                "s1": max(start_state.mastery.s1, int(pm.get("s1", start_state.mastery.s1))),
                "s2": max(start_state.mastery.s2, int(pm.get("s2", start_state.mastery.s2))),
                "s3": max(start_state.mastery.s3, int(pm.get("s3", start_state.mastery.s3))),
            }

        t1, t2, t3 = st.columns(3)
        elite_options = list(range(start_state.elite, 3))
        target_elite = t1.selectbox(
            "Target Elite",
            elite_options,
            index=elite_options.index(min(2, max(start_state.elite, target_elite_default))),
            key=f"target_e_{cid}_{preset}",
        )
        max_target = phase_max_level(constants, rarity, target_elite)
        min_target = start_state.level if target_elite == start_state.elite else 1
        target_level = t2.number_input(
            "Target level",
            min_value=min_target,
            max_value=max_target,
            value=min(max_target, max(min_target, int(target_level_default))),
            step=1,
            key=f"target_l_{cid}_{preset}_{target_elite}",
        )
        skill_options = list(range(start_state.skill_level, 8))
        target_skill = t3.selectbox(
            "Target skill",
            skill_options,
            index=skill_options.index(min(7, max(start_state.skill_level, target_skill_default))),
            key=f"target_sl_{cid}_{preset}",
        )

        mastery_mode = st.radio(
            "Mastery shortcut",
            ["Keep current", "S1M3", "S2M3", "S3M3", "Custom"],
            horizontal=True,
            key=f"mastery_shortcut_{cid}",
        )
        if mastery_mode == "S1M3":
            mastery_defaults["s1"] = 3
        elif mastery_mode == "S2M3":
            mastery_defaults["s2"] = 3
        elif mastery_mode == "S3M3":
            mastery_defaults["s3"] = 3
        elif mastery_mode == "Keep current":
            mastery_defaults = {
                "s1": start_state.mastery.s1,
                "s2": start_state.mastery.s2,
                "s3": start_state.mastery.s3,
            }

        if mastery_mode == "Custom":
            mm1, mm2, mm3 = st.columns(3)
            s1_opts = list(range(start_state.mastery.s1, 4))
            s2_opts = list(range(start_state.mastery.s2, 4))
            s3_opts = list(range(start_state.mastery.s3, 4))
            target_s1 = mm1.selectbox("S1", s1_opts, index=s1_opts.index(max(start_state.mastery.s1, mastery_defaults["s1"])), key=f"ts1_{cid}")
            target_s2 = mm2.selectbox("S2", s2_opts, index=s2_opts.index(max(start_state.mastery.s2, mastery_defaults["s2"])), key=f"ts2_{cid}")
            target_s3 = mm3.selectbox("S3", s3_opts, index=s3_opts.index(max(start_state.mastery.s3, mastery_defaults["s3"])), key=f"ts3_{cid}")
        else:
            target_s1 = max(start_state.mastery.s1, mastery_defaults["s1"])
            target_s2 = max(start_state.mastery.s2, mastery_defaults["s2"])
            target_s3 = max(start_state.mastery.s3, mastery_defaults["s3"])
            st.caption(f"Masteries → S1 M{target_s1} · S2 M{target_s2} · S3 M{target_s3}")

        module_defs = module_catalog_for_operator(modules, cid, en_modules)
        target_module_id = None
        target_module_level = 0
        if module_defs:
            module_choices = [""] + list(module_defs)
            saved_mid = str(saved_target.get("module_id") or "")
            if saved_mid not in module_choices:
                saved_mid = ""
            mc1, mc2 = st.columns([3, 1])
            target_module_id = mc1.selectbox(
                "Module",
                module_choices,
                index=module_choices.index(saved_mid),
                format_func=lambda mid: "No module upgrade" if not mid else str(module_defs[mid]["name"]).strip("'\""),
                key=f"target_module_{cid}",
            )
            if target_module_id:
                current_mod = start_state.modules.get(target_module_id, ModuleProgress()).level
                level_opts = list(range(current_mod, 4))
                target_module_level = mc2.selectbox(
                    "Target module",
                    level_opts,
                    index=len(level_opts)-1,
                    key=f"target_mod_lvl_{cid}_{target_module_id}",
                )

        action_label = "Save changes" if editing_goal else "Add to plan"
        a1, a2 = st.columns([1.5, 4.5])
        if a1.button(action_label, type="primary", key=f"save_goal_{cid}"):
            try:
                t0 = time.perf_counter()
                target = UpgradeGoal(
                    operator_id=cid,
                    elite=int(target_elite),
                    level=int(target_level),
                    skill_level=int(target_skill),
                    mastery=SkillState(
                        s1=int(target_s1), s2=int(target_s2), s3=int(target_s3)
                    ),
                    module_id=target_module_id or None,
                    module_level=int(target_module_level),
                )
                model = build_operator_cost_model(cid, chars, modules, en_modules)
                cost = calculate_upgrade_cost(
                    current=start_state,
                    target=target,
                    model=model,
                    constants=constants,
                    leveling_fn=leveling_cost,
                )
                goal = {
                    "operator": meta["name"],
                    "operator_id": cid,
                    "active": bool(editing_goal.get("active", True)) if editing_goal else True,
                    "current": start_state.model_dump(),
                    "target": target.model_dump(),
                    "module_name": (
                        str(module_defs[target_module_id]["name"]).strip("'\"")
                        if target_module_id else ""
                    ),
                }
                idx = next(
                    (i for i,g in enumerate(st.session_state.goals) if g.get("operator_id") == cid),
                    None,
                )
                if idx is None:
                    st.session_state.goals.append(goal)
                    st.session_state.costs.append(cost.model_dump())
                else:
                    st.session_state.goals[idx] = goal
                    st.session_state.costs[idx] = cost.model_dump()

                mark_performance("last goal calculation", time.perf_counter() - t0)
                st.session_state.editing_goal_id = None
                clear_planner_selection()
                persist_profile()
                st.success(f'Saved {meta["name"]}. The picker is ready for the next operator.')
                st.rerun()
            except Exception as exc:
                st.error(str(exc))
        a2.caption("No extra navigation step after saving — choose the next operator immediately.")


# ---------------------------
# Farming
# ---------------------------
elif page == "Farming":
    st.subheader("Farming")
    pairs = active_goal_pairs(st.session_state.goals, st.session_state.costs)
    if not st.session_state.goals:
        st.info("Add at least one planning goal first.")
    elif not pairs:
        st.info("All saved goals are paused. Activate at least one goal in Planner.")
    else:
        goals = [g for g,_ in pairs]
        costs = [CostBundle.model_validate(c) for _,c in pairs]
        total = aggregate_costs(costs)
        inv = st.session_state.inventory
        st.caption(f"{len(goals)} active goal{'s' if len(goals)!=1 else ''} included · {len(st.session_state.goals)-len(goals)} paused")

        view = top_nav(
            ["Reserve", "Crafting", "Stages", "Summary"],
            selected=st.session_state.get("farming_view", "Reserve"),
            key="rhodes_farming_nav",
        )
        if view:
            st.session_state.farming_view = view
        else:
            view = st.session_state.get("farming_view", "Reserve")

        if view == "Reserve":
            st.markdown("### LMD & EXP reserve")
            r1, r2 = st.columns(2)
            reserve_lmd = r1.number_input(
                "LMD to keep",
                min_value=0, max_value=int(inv.lmd),
                value=min(int(inv.lmd), int(st.session_state.reserve_lmd)),
                step=1000,
            )
            reserve_exp = r2.number_input(
                "EXP to keep",
                min_value=0, max_value=int(inv.exp),
                value=min(int(inv.exp), int(st.session_state.reserve_exp)),
                step=1000,
                help="Raw EXP points. T1 Drill = 200, T2 Frontline = 400, T3 Tactical = 1,000, T4 Strategic = 2,000 EXP. RIIC base production is modelled only as T3 Tactical Records.",
            )
            b1, b2, b3, b4 = st.columns(4)
            if b1.button("Reserve all LMD"):
                reserve_lmd = int(inv.lmd)
                st.session_state.reserve_lmd = reserve_lmd
                persist_profile()
                st.rerun()
            if b2.button("Clear LMD reserve"):
                st.session_state.reserve_lmd = 0
                persist_profile()
                st.rerun()
            if b3.button("Reserve all EXP"):
                st.session_state.reserve_exp = int(inv.exp)
                persist_profile()
                st.rerun()
            if b4.button("Clear EXP reserve"):
                st.session_state.reserve_exp = 0
                persist_profile()
                st.rerun()

            st.session_state.reserve_lmd = int(reserve_lmd)
            st.session_state.reserve_exp = int(reserve_exp)

            st.markdown("### Material reserve")
            x1, x2 = st.columns(2)
            if x1.button("Reserve all owned materials in active plan"):
                for iid in total.materials:
                    st.session_state.reserve_qty[iid] = float(inv.materials.get(iid, 0) or 0)
                persist_profile()
                st.rerun()
            if x2.button("Clear material reserves"):
                st.session_state.reserve_qty = {}
                persist_profile()
                st.rerun()

            rows = []
            for iid, req in sorted(total.materials.items(), key=lambda kv: item_names.get(kv[0],kv[0]).casefold()):
                owned = float(inv.materials.get(iid,0) or 0)
                reserve = min(owned, float(st.session_state.reserve_qty.get(iid,0) or 0))
                rows.append({
                    "Icon": item_icon_url(iid, item_meta),
                    "Material": item_names.get(iid,iid),
                    "Required": req,
                    "Owned": owned,
                    "Reserve": reserve,
                    "Spendable": max(0.0, owned-reserve),
                    "Item ID": iid,
                })
            edited = st.data_editor(
                pd.DataFrame(rows),
                use_container_width=True,
                hide_index=True,
                disabled=["Icon","Material","Required","Owned","Spendable","Item ID"],
                column_config={
                    "Icon": st.column_config.ImageColumn(" ", width="small"),
                    "Reserve": st.column_config.NumberColumn("Reserve", min_value=0, step=1),
                    "Item ID": None,
                },
                key="full_reserve_editor",
            )
            new_reserves = {}
            for _, row in edited.iterrows():
                iid = str(row["Item ID"])
                owned = float(inv.materials.get(iid,0) or 0)
                qty = min(owned, max(0.0, float(row["Reserve"] or 0)))
                if qty > 0:
                    new_reserves[iid] = qty
            if new_reserves != st.session_state.reserve_qty:
                st.session_state.reserve_qty = new_reserves
                persist_profile()

        # Shared calculation cached in session by signature.
        sig = plan_signature(
            goals=goals,
            costs=[c.model_dump() for c in costs],
            inventory=inv,
            reserves=st.session_state.reserve_qty,
            reserve_lmd=st.session_state.reserve_lmd,
            reserve_exp=st.session_state.reserve_exp,
            planning_days=st.session_state.planning_days,
            base_lmd_per_day=st.session_state.base_lmd_per_day,
            base_t3_per_day=st.session_state.base_t3_per_day,
        )
        cache = st.session_state.get("_farming_calc_cache")
        if not cache or cache.get("signature") != sig:
            t0 = time.perf_counter()
            spendable = spendable_inventory(
                inv,
                reserved_materials=st.session_state.reserve_qty,
                reserved_lmd=st.session_state.reserve_lmd,
                reserved_exp=st.session_state.reserve_exp,
            )
            craft_result = simulate_crafting(
                required=total.materials,
                owned=spendable.materials,
                recipes=recipes,
                reserved_items=set(),
            )
            expansion = expand_high_tier_farm_targets(
                remaining=craft_result["remaining"],
                stock_after=craft_result["stock_after"],
                recipes=recipes,
                item_meta=item_meta,
                stop_tier=3,
            )
            gross_lmd = total.lmd + craft_result["lmd_crafting"] + expansion["lmd_crafting"]
            lmd_before_base = max(0, int(gross_lmd)-int(spendable.lmd))
            exp_before_base = max(0, int(total.exp)-int(spendable.exp))
            cache = {
                "signature": sig,
                "spendable": spendable.model_dump(),
                "craft_result": craft_result,
                "expansion": expansion,
                "gross_lmd": gross_lmd,
                "lmd_before_base": lmd_before_base,
                "exp_before_base": exp_before_base,
            }
            st.session_state["_farming_calc_cache"] = cache
            mark_performance("farming core calculation", time.perf_counter()-t0)

        spendable = Inventory.model_validate(cache["spendable"])
        craft_result = cache["craft_result"]
        expansion = cache["expansion"]
        lmd_before_base = int(cache["lmd_before_base"])
        exp_before_base = int(cache["exp_before_base"])

        if view == "Crafting":
            st.markdown("### Craft now")
            if craft_result["craft_ops"]:
                rows = []
                for op in craft_result["craft_ops"]:
                    ingredients = ", ".join(
                        f'{item_names.get(iid, iid)} ×{int(qty) if float(qty).is_integer() else qty:g}'
                        for iid, qty in op.get("ingredients", {}).items()
                    )
                    rows.append({
                        "Icon": item_icon_url(op["output_id"], item_meta),
                        "Craft": item_names.get(op["output_id"],op["output_id"]),
                        "Batches": op["batches"],
                        "Output": op["output_quantity"],
                        "Uses": ingredients,
                        "LMD": op["lmd_cost"],
                    })
                st.dataframe(
                    pd.DataFrame(rows),
                    use_container_width=True,
                    hide_index=True,
                    column_config={"Icon": st.column_config.ImageColumn(" ", width="small")},
                )
            else:
                st.success("Nothing needs immediate crafting from current spendable stock.")

            st.markdown("### Craft after farming")
            if expansion["future_craft_ops"]:
                rows = []
                for op in expansion["future_craft_ops"]:
                    ingredients = ", ".join(
                        f'{item_names.get(iid, iid)} ×{int(qty) if float(qty).is_integer() else qty:g}'
                        for iid, qty in op.get("ingredients", {}).items()
                    )
                    rows.append({
                        "Icon": item_icon_url(op["output_id"], item_meta),
                        "Craft": item_names.get(op["output_id"],op["output_id"]),
                        "Batches": op["batches"],
                        "Output": op["output_quantity"],
                        "Uses after farming": ingredients,
                        "LMD": op["lmd_cost"],
                    })
                st.dataframe(
                    pd.DataFrame(rows),
                    use_container_width=True,
                    hide_index=True,
                    column_config={"Icon": st.column_config.ImageColumn(" ", width="small")},
                )
            else:
                st.caption("No future high-tier crafting required.")

        elif view == "Stages":
            st.markdown("### Passive base assumptions")
            p1,p2,p3 = st.columns(3)
            days = p1.number_input("Horizon days", min_value=0.0, value=float(st.session_state.planning_days), step=1.0, key="stage_days")
            base_lmd = p2.number_input("Base LMD/day", min_value=0, value=int(st.session_state.base_lmd_per_day), step=1000, key="stage_lmd")
            base_t3 = p3.number_input("Base T3 Tactical Records / day", min_value=0, value=int(st.session_state.base_t3_per_day), step=1, key="stage_t3")
            if (
                float(days) != float(st.session_state.planning_days)
                or int(base_lmd) != int(st.session_state.base_lmd_per_day)
                or int(base_t3) != int(st.session_state.base_t3_per_day)
            ):
                st.session_state.planning_days = float(days)
                st.session_state.base_lmd_per_day = int(base_lmd)
                st.session_state.base_t3_per_day = int(base_t3)
                persist_profile()

            lmd_after = max(0, lmd_before_base-int(base_lmd*days))
            exp_after = max(0, exp_before_base-int(base_t3*1000*days))
            resolved_materials, acquisition_notes = resolve_special_acquisitions(
                expansion["farm_targets"],
                spendable,
            )
            final = CostBundle(lmd=lmd_after, exp=exp_after, materials=resolved_materials)

            # Purchase Certificates should normally be present in Penguin.
            # If the selected matrix omits AP-5, provide the stable in-game AP-5 fallback.
            farming_stages = list(stages)
            ap5_fallback_used = False
            if final.materials.get("4006", 0) > 0 and best_stage_for_item("4006", farming_stages) is None:
                ap5_fallback_used = True
                farming_stages.append(
                    StageModel(
                        stage_id="AP-5-fallback",
                        code="AP-5",
                        sanity_cost=30,
                        drops=[{"item_id": "4006", "expected_per_run": 21.0}],
                    )
                )

            t0 = time.perf_counter()
            farm = build_farming_plan(final, farming_stages)
            mark_performance("last stage plan", time.perf_counter()-t0)

            unavailable = {
                iid: qty for iid,qty in final.materials.items()
                if qty > 0 and best_stage_for_item(iid, farming_stages) is None
            }

            if acquisition_notes:
                st.markdown("#### Shop / acquisition conversion")
                for note in acquisition_notes:
                    st.info(note["summary"])
            if ap5_fallback_used:
                st.caption(
                    "AP-5 fallback used because Penguin Statistics did not return a Purchase Certificate route "
                    "for the selected server. Rhodes uses 30 sanity and approximately 21 Purchase Certificates per run."
                )

            if unavailable:
                st.warning(
                    f"{len(unavailable)} required material"
                    f'{"s" if len(unavailable) != 1 else ""} '
                    "still cannot be mapped to a farming route."
                )
                missing_rows = []
                for iid, qty in sorted(
                    unavailable.items(),
                    key=lambda kv: item_names.get(kv[0], kv[0]).casefold(),
                ):
                    missing_rows.append({
                        "Icon": item_icon_url(iid, item_meta),
                        "Material": item_names.get(iid, iid),
                        "Required": qty,
                        "Reason": (
                            "CN only / future EN"
                            if iid not in en_item_meta
                            else f"No farming/acquisition route returned for {server}"
                        ),
                    })
                st.dataframe(
                    pd.DataFrame(missing_rows),
                    use_container_width=True,
                    hide_index=True,
                    height=min(360, 54 + 38 * len(missing_rows)),
                    column_config={"Icon": st.column_config.ImageColumn(" ", width="small")},
                )

            if farm.lines:
                stage_rows = [
                    farming_line_display(row, acquisition_notes)
                    for row in farm.lines
                ]
                st.dataframe(
                    pd.DataFrame(stage_rows),
                    use_container_width=True,
                    hide_index=True,
                    height=420,
                    column_config={
                        "Icon": st.column_config.ImageColumn(" ", width="small"),
                    },
                )
                st.metric("Total sanity", f"{farm.total_sanity:,}")
            elif not unavailable:
                st.success("Nothing remains to farm.")


        elif view == "Summary":
            st.markdown("### Farming summary")
            st.caption(
                "Final checklist after active goals, stash, reserves, crafting, "
                "shop conversions and passive RIIC production."
            )
            st.caption(
                f"RIIC forecast: {st.session_state.planning_days:g} day(s) · "
                f"{int(st.session_state.base_lmd_per_day):,} LMD/day · "
                f"{int(st.session_state.base_t3_per_day):,} T3 Tactical Battle Records/day."
            )

            days = float(st.session_state.planning_days)
            base_lmd = int(st.session_state.base_lmd_per_day)
            base_t3 = int(st.session_state.base_t3_per_day)

            lmd_after = max(0, lmd_before_base - int(base_lmd * days))
            exp_after = max(0, exp_before_base - int(base_t3 * 1000 * days))

            resolved_materials, acquisition_notes = resolve_special_acquisitions(
                expansion["farm_targets"],
                spendable,
            )
            final = CostBundle(
                lmd=lmd_after,
                exp=exp_after,
                materials=resolved_materials,
            )

            farming_stages = list(stages)
            ap5_fallback_used = False
            if final.materials.get("4006", 0) > 0 and best_stage_for_item("4006", farming_stages) is None:
                ap5_fallback_used = True
                farming_stages.append(
                    StageModel(
                        stage_id="AP-5-fallback",
                        code="AP-5",
                        sanity_cost=30,
                        drops=[{"item_id": "4006", "expected_per_run": 21.0}],
                    )
                )

            farm = build_farming_plan(final, farming_stages)
            unavailable = {
                iid: qty
                for iid, qty in final.materials.items()
                if qty > 0 and best_stage_for_item(iid, farming_stages) is None
            }

            s1, s2, s3, s4 = st.columns(4)
            s1.metric("Active goals", len(goals))
            s2.metric("Stages", len(farm.lines))
            s3.metric("Total runs", sum(int(row.runs) for row in farm.lines))
            s4.metric("Total sanity", f"{farm.total_sanity:,}")

            if acquisition_notes:
                st.markdown("#### Acquisition notes")
                for note in acquisition_notes:
                    st.info(note["summary"])
            if ap5_fallback_used:
                st.caption(
                    "AP-5 fallback used because Penguin Statistics did not return a Purchase Certificate route "
                    "for the selected server: 30 sanity, approximately 21 Purchase Certificates per run."
                )

            if farm.lines:
                summary_rows = [
                    farming_line_display(row, acquisition_notes)
                    for row in farm.lines
                ]
                st.dataframe(
                    pd.DataFrame(summary_rows),
                    use_container_width=True,
                    hide_index=True,
                    height=min(480, 54 + 38 * len(summary_rows)),
                    column_config={
                        "Icon": st.column_config.ImageColumn(" ", width="small"),
                    },
                )
            else:
                st.success("No stage farming remains for the active goals.")

            if unavailable:
                st.markdown("#### Not yet mapped")
                missing_rows = [
                    {
                        "Icon": item_icon_url(iid, item_meta),
                        "Material": item_names.get(iid, iid),
                        "Required": qty,
                        "Reason": (
                            "CN only / future EN"
                            if iid not in en_item_meta
                            else f"No farming/acquisition route returned for {server}"
                        ),
                    }
                    for iid, qty in sorted(
                        unavailable.items(),
                        key=lambda kv: item_names.get(kv[0], kv[0]).casefold(),
                    )
                ]
                st.dataframe(
                    pd.DataFrame(missing_rows),
                    use_container_width=True,
                    hide_index=True,
                    column_config={"Icon": st.column_config.ImageColumn(" ", width="small")},
                )

            st.markdown("### Penguin Statistics")
            try:
                config_json = build_penguin_planner_config_json(
                    inventory=inv,
                    farm_targets=final.materials,
                    additional_lmd=final.lmd,
                    additional_exp=final.exp,
                    item_meta=item_meta,
                )
                p1, p2 = st.columns([1.25, 1.0])
                with p1:
                    clipboard_button(config_json)
                with p2:
                    st.download_button(
                        "⬇ Download config",
                        data=config_json,
                        file_name="rhodes_penguin_statistics_planner.json",
                        mime="application/json",
                        use_container_width=True,
                    )
                st.caption(
                    "Copy is usually the fastest route: paste the configuration "
                    "into Penguin Statistics Planner."
                )
            except Exception as exc:
                st.warning(f"Penguin Statistics export unavailable: {exc}")

flush_browser_profile_save()
