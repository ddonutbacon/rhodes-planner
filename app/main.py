from __future__ import annotations

import html
import json
import sys

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from rhodes import __version__
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
    profession_label,
)
from rhodes.adapters.http import clear_cache
from rhodes.adapters.penguin import fetch_penguin_matrix, normalize_stages
from rhodes.adapters.penguin_export import build_penguin_planner_config_json
from rhodes.core.crafting import (
    expand_high_tier_farm_targets,
    expand_reserved_requirements,
    merge_farm_expansions,
    parse_workshop_recipes,
    add_dualchip_factory_recipes,
    simulate_crafting,
)
from rhodes.core.farming import build_farming_plan, best_stage_for_item
from rhodes.core.formatting import fmt_num
from rhodes.core.models import (
    CostBundle,
    Inventory,
    ModuleProgress,
    OperatorState,
    SkillState,
    StageModel,
    UpgradeGoal,
)
from rhodes.core.planner import (
    aggregate_costs,
    calculate_deficit,
    calculate_upgrade_cost,
)
from rhodes.core.profile_store import (
    clear_profile,
    load_profile,
    profile_path,
    save_profile,
)


st.set_page_config(
    page_title="Rhodes Planner",
    page_icon="🧭",
    layout="wide",
)

st.markdown(
    """
<style>
.block-container {max-width: 1240px; padding-top: 2rem;}
div[data-testid="stMetric"] {
    border: 1px solid rgba(128,128,128,.25);
    padding: 12px;
    border-radius: 12px;
}
.operator-card {
    display:flex;
    gap:18px;
    align-items:center;
    border:1px solid rgba(128,128,128,.20);
    border-radius:14px;
    padding:14px 16px;
    margin:8px 0 18px 0;
}
.operator-title {font-size:1.35rem;font-weight:700;}
.operator-sub {opacity:.72;}
.mat-chip {display:inline-flex;align-items:center;gap:5px;border:1px solid rgba(128,128,128,.25);border-radius:10px;padding:4px 7px;margin:3px 5px 3px 0;background:rgba(128,128,128,.06);font-weight:600;}
.mat-chip img {width:30px;height:30px;object-fit:contain;}
.muted-note {opacity:.65;font-style:italic;}
</style>
""",
    unsafe_allow_html=True,
)


CLASS_ORDER = [
    "Vanguard",
    "Guard",
    "Defender",
    "Sniper",
    "Caster",
    "Medic",
    "Supporter",
    "Specialist",
]

EXP_VALUES = {
    "2001": 200,
    "2002": 400,
    "2003": 1000,
    "2004": 2000,
}


def material_chips_html(bundle: CostBundle, item_meta: dict, item_names: dict) -> str:
    """Compact, traceable material list for operator and aggregate requirements."""
    chips = []
    for iid, qty in sorted(
        bundle.materials.items(),
        key=lambda kv: item_names.get(kv[0], kv[0]).lower(),
    ):
        name = html.escape(str(item_names.get(iid, iid)))
        icon = html.escape(item_icon_url(iid, item_meta), quote=True)
        chips.append(
            f'<span class="mat-chip" title="{name}">'
            f'<img src="{icon}" alt="{name}">'
            f'<span>× {html.escape(fmt_num(qty))}</span>'
            f'</span>'
        )
    if not chips:
        return '<span class="muted-note">No material items required.</span>'
    return ''.join(chips)


def render_cost_breakdown(bundle: CostBundle, item_meta: dict, item_names: dict) -> None:
    st.markdown(material_chips_html(bundle, item_meta, item_names), unsafe_allow_html=True)
    aux = []
    if bundle.lmd:
        aux.append(f"LMD × {bundle.lmd:,}")
    if bundle.exp:
        aux.append(f"EXP × {bundle.exp:,} ({bundle.exp/1000:,.1f} T3 equiv.)")
    if aux:
        st.caption(' · '.join(aux))



def load_sample():
    return json.loads(
        (ROOT / "rhodes/data/sample.json").read_text(encoding="utf-8")
    )


@st.cache_data(show_spinner=False)
def get_live_data(server):
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
        chars, items, constants, modules, building, en_chars, en_items, en_modules,
        [x.model_dump() for x in stages], penguin_error,
    )


def get_data(mode, server):
    if mode == "Live":
        (
            chars, items, constants, modules, building, en_chars, en_items, en_modules,
            stage_dicts, penguin_error,
        ) = get_live_data(server)
        return (
            chars, items, constants, modules, building, en_chars, en_items, en_modules,
            [StageModel.model_validate(x) for x in stage_dicts],
            False, penguin_error,
        )

    sample = load_sample()
    return (
        sample["characters"], sample["items"], sample["constants"],
        sample["modules"], {}, sample["characters"], sample["items"], sample["modules"],
        [StageModel.model_validate(x) for x in sample["stages"]],
        True, None,
    )


def exp_from_cards(inv: Inventory) -> int:
    return sum(
        int(inv.exp_cards.get(iid, 0) or 0) * value
        for iid, value in EXP_VALUES.items()
    )


def ensure_state():
    if st.session_state.get("_profile_loaded"):
        return

    saved = load_profile()

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
    st.session_state.reserved_materials = set(
        saved.get("reserved_materials") or []
    )
    st.session_state.arkprts_meta = None
    st.session_state.farm_full_lmd = bool(
        settings.get("farm_full_lmd", False)
    )
    st.session_state.farm_full_exp = bool(
        settings.get("farm_full_exp", False)
    )
    st.session_state.planning_days = float(
        settings.get("planning_days", 7.0)
    )
    st.session_state.base_lmd_per_day = int(
        settings.get("base_lmd_per_day", 0)
    )
    st.session_state.base_t3_per_day = int(
        settings.get("base_t3_per_day", 0)
    )
    st.session_state.profile_epoch = int(saved.get("profile_epoch", 0) or 0)
    st.session_state.editing_goal_id = None
    st.session_state.edit_epoch = 0
    st.session_state._profile_loaded = True


def persist_profile():
    save_profile({
        "schema_version": 5,
        "profile_epoch": int(st.session_state.get("profile_epoch", 0)),
        "inventory": st.session_state.inventory.model_dump(),
        "operators": {
            cid: op.model_dump()
            for cid, op in st.session_state.operators.items()
        },
        "goals": st.session_state.goals,
        "costs": st.session_state.costs,
        "reserved_materials": sorted(
            st.session_state.reserved_materials
        ),
        "settings": {
            "farm_full_lmd": bool(
                st.session_state.get("farm_full_lmd", False)
            ),
            "farm_full_exp": bool(
                st.session_state.get("farm_full_exp", False)
            ),
            "planning_days": float(
                st.session_state.get("planning_days", 7.0)
            ),
            "base_lmd_per_day": int(
                st.session_state.get("base_lmd_per_day", 0)
            ),
            "base_t3_per_day": int(
                st.session_state.get("base_t3_per_day", 0)
            ),
        },
    })


def bump_profile_epoch():
    st.session_state.profile_epoch = int(
        st.session_state.get("profile_epoch", 0)
    ) + 1


def item_tier(raw_rarity) -> int:
    if isinstance(raw_rarity, str):
        value = raw_rarity.upper()
        if value.startswith("TIER_"):
            try:
                return int(value.split("_", 1)[1])
            except ValueError:
                return 0
        try:
            n = int(value)
            return n + 1 if 0 <= n <= 4 else n
        except ValueError:
            return 0

    if isinstance(raw_rarity, (int, float)):
        n = int(raw_rarity)
        return n + 1 if 0 <= n <= 4 else n

    return 0


def operator_rows(
    catalog,
    account_operators,
    search_text,
    selected_classes,
    selected_rarities,
    owned_only,
    future_only=False,
):
    search = str(search_text or "").strip().lower()
    classes = set(selected_classes or [])
    rarities = set(selected_rarities or [])
    rows = []

    for cid, meta in catalog.items():
        op = account_operators.get(cid)
        owned = op is not None

        if owned_only and not owned:
            continue
        if future_only and meta.get("available_on_en", True):
            continue
        if classes and meta.get("class") not in classes:
            continue
        if rarities and meta.get("rarity") not in rarities:
            continue
        if search:
            haystack = " ".join([
                str(meta.get("name", "")),
                str(meta.get("cn_name", "")),
                str(cid),
            ]).lower()
            if search not in haystack:
                continue

        rows.append({
            "Select": False,
            "Portrait": operator_avatar_url(cid),
            "Operator": meta.get("name", cid),
            "Class": meta.get(
                "class",
                profession_label(meta.get("profession", "")),
            ),
            "Rarity": meta.get("rarity", 0),
            "Owned": "Yes" if owned else "No",
            "Availability": meta.get("availability", "EN"),
            "Elite": op.elite if op else 0,
            "Level": op.level if op else 1,
            "Char ID": cid,
        })

    rows.sort(
        key=lambda x: (-x["Rarity"], x["Operator"].lower())
    )
    return rows


def operator_selector_table(
    prefix,
    catalog,
    account_operators,
    *,
    owned_default,
):
    f1, f2, f3 = st.columns([2.2, 1.5, 1.5])

    search = f1.text_input(
        "Search operator",
        placeholder="Type a name...",
        key=f"{prefix}_search",
    )
    classes = f2.multiselect(
        "Class",
        CLASS_ORDER,
        key=f"{prefix}_classes",
    )
    rarities = f3.multiselect(
        "Rarity",
        [6, 5, 4, 3, 2, 1],
        key=f"{prefix}_rarities",
    )

    t1, t2 = st.columns(2)
    owned_only = t1.toggle(
        "Owned operators only",
        value=owned_default,
        key=f"{prefix}_owned_only",
    )
    future_only = t2.toggle(
        "CN-only operators only",
        value=False,
        key=f"{prefix}_future_only",
        help="Useful for browsing operators that are known in CN data but not yet present in the EN snapshot.",
    )

    rows = operator_rows(
        catalog,
        account_operators,
        search,
        classes,
        rarities,
        owned_only,
        future_only,
    )

    if not rows:
        st.info("No operators match the current filters.")
        return None

    edited = st.data_editor(
        pd.DataFrame(rows),
        use_container_width=True,
        hide_index=True,
        disabled=[
            "Portrait",
            "Operator",
            "Class",
            "Rarity",
            "Owned",
            "Availability",
            "Elite",
            "Level",
            "Char ID",
        ],
        column_config={
            "Select": st.column_config.CheckboxColumn(
                "Select",
                width="small",
            ),
            "Portrait": st.column_config.ImageColumn(
                " ",
                width="small",
            ),
            "Char ID": None,
        },
        key=f"{prefix}_table_{st.session_state.get('profile_epoch', 0)}",
    )

    selected = edited.loc[edited["Select"] == True]

    if selected.empty:
        st.caption("Tick one row to select an operator.")
        return None

    if len(selected) > 1:
        st.warning(
            "Please select one operator. The first checked row is used."
        )

    return str(selected.iloc[0]["Char ID"])


def clipboard_button(text: str, *, label: str = "Copy Penguin config"):
    """Render a one-click clipboard button with a legacy fallback."""
    payload = json.dumps(str(text))
    components.html(
        f"""
        <div style="display:flex;align-items:center;gap:10px;font-family:system-ui,sans-serif;">
          <button id="copyBtn" style="
              border:1px solid #4b5563;
              background:#1f2937;
              color:#fff;
              padding:9px 14px;
              border-radius:8px;
              cursor:pointer;
              font-size:14px;">
            📋 {html.escape(label)}
          </button>
          <span id="copyStatus" style="font-size:13px;color:#9ca3af;"></span>
        </div>
        <script>
          const payload = {payload};
          const btn = document.getElementById("copyBtn");
          const status = document.getElementById("copyStatus");

          async function copyText() {{
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
              status.textContent = "Copy failed — use the preview below.";
            }}
          }}

          btn.addEventListener("click", copyText);
        </script>
        """,
        height=46,
    )


ensure_state()

st.title("🧭 Rhodes Planner")
st.caption(
    "Turn your current account into a clear upgrade plan, crafting route, "
    "and farming checklist."
)

if "_flash_message" in st.session_state:
    st.success(st.session_state.pop("_flash_message"))

with st.sidebar:
    st.header("Data")

    mode = st.radio(
        "Source",
        ["Live", "Offline demo"],
        index=0,
    )
    server = st.selectbox(
        "Farming server (Penguin)",
        ["US", "JP", "KR", "CN"],
        index=0,
        help="Controls farming/drop availability only. The operator progression catalog always uses the latest CN game data.",
    )
    st.caption("Planner knowledge: latest CN · EN snapshot used for availability/localization")

    if st.button("Clear downloaded public-data cache"):
        clear_cache()
        st.cache_data.clear()
        st.success("Public-data cache cleared.")

    st.divider()
    st.markdown("**Local profile**")
    st.caption("Auto-save: private OS user application-data directory")

    confirm_nuke = st.checkbox(
        "I understand this permanently clears my saved Rhodes profile",
        key="confirm_nuke",
    )

    if st.button(
        "☢ Nuke / clear local profile",
        disabled=not confirm_nuke,
    ):
        clear_profile()
        st.session_state.clear()
        st.rerun()

    with st.expander("Diagnostics / bug report"):
        diagnostic = {
            "rhodes_version": __version__,
            "profile_exists": profile_path().exists(),
            "operators": len(st.session_state.operators),
            "inventory_entries": len(st.session_state.inventory.materials),
            "nonzero_inventory_entries": sum(
                1 for value in st.session_state.inventory.materials.values()
                if value > 0
            ),
            "goals": len(st.session_state.goals),
                        "profile_epoch": int(st.session_state.get("profile_epoch", 0)),
        }
        st.json(diagnostic)
        st.download_button(
            "Download diagnostic JSON",
            data=json.dumps(diagnostic, indent=2),
            file_name="rhodes_diagnostic.json",
            mime="application/json",
        )
        st.caption(
            "This diagnostic contains structural counts only, not the raw "
            "ArkPRTS export, currencies, inventory quantities, or account identifiers."
        )

    st.divider()
    st.markdown("**External sources**")
    st.caption("ArknightsAssets / ArknightsGamedata")
    st.caption("Penguin Statistics")
    st.caption("ArkPRTS full-account export")
    st.caption("Community image repositories")

try:
    with st.spinner("Loading game data..."):
        (
            chars, items, constants, modules, building, en_chars, en_items, en_modules,
            stages, is_demo, penguin_error,
        ) = get_data(mode, server)
except Exception as exc:
    st.error(
        "Core live game-data sync failed. "
        "Rhodes Planner switched to the offline demo dataset."
    )
    st.code(str(exc))
    (
        chars, items, constants, modules, building, en_chars, en_items, en_modules,
        stages, is_demo, penguin_error,
    ) = get_data("Offline demo", server)

catalog = operator_catalog(chars, en_chars)
item_meta = build_item_metadata_map(items, en_items)
en_item_meta = build_item_metadata_map(en_items)
item_names = {
    iid: meta["name"]
    for iid, meta in item_meta.items()
}

# Refresh persisted display names from the current localization layer.
# v0.7.0 could save raw CN names for future operators; IDs remain the source
# of truth, so existing plans can be upgraded in place without re-adding them.
for _goal in st.session_state.goals:
    _cid = str(_goal.get("operator_id") or "")
    if _cid in catalog:
        _goal["operator"] = catalog[_cid]["name"]
for _cid, _op in st.session_state.operators.items():
    if _cid in catalog:
        _op.name = catalog[_cid]["name"]

advancement_ids = advancement_item_ids(
    chars,
    modules,
    item_meta,
)
recipes = add_dualchip_factory_recipes(
    parse_workshop_recipes(building),
    item_meta,
)

if is_demo:
    st.warning(
        "Offline demo mode uses synthetic data. "
        "Use Live mode for real game data."
    )
elif penguin_error:
    st.warning(
        "Operator/account data loaded, but Penguin Statistics farming data "
        "is unavailable. Account and upgrade planning still work."
    )
    with st.expander("Farming-data connection detail"):
        st.code(penguin_error)

page = st.radio(
    "Navigation",
    ["Credits & Sources", "Dashboard", "Account", "Planner", "Farming", "About"],
    horizontal=True,
    label_visibility="collapsed",
    key="active_page",
)

# =====================================================================
# Credits & Sources
# =====================================================================
if page == "Credits & Sources":
    st.subheader("Credits & Sources")
    st.caption(
        "Rhodes Planner is an unofficial fan-made personal toolkit. "
        "It is not affiliated with or endorsed by Hypergryph, Yostar, "
        "Penguin Statistics, ArkPRTS, or the other community projects below."
    )

    st.markdown(
        """
### Arknights game content
Arknights and related game data/art remain the property of their respective
rights holders, including **Hypergryph** and **Yostar**. Rhodes Planner does
not bundle a game-data snapshot; it retrieves selected progression data at
runtime.

### Game data
- **ArknightsAssets / ArknightsGamedata**  \n  Runtime source for operator metadata, item metadata, progression costs,
  modules, stages and workshop formulas.  \n  https://github.com/ArknightsAssets/ArknightsGamedata

### Farming statistics and interoperability
- **Penguin Statistics**  \n  Community drop statistics used for material farming recommendations. Penguin's
  public API documentation asks API users to follow **CC BY-NC 4.0**, so the
  dataset-dependent workflow is intended for non-commercial fan/portfolio use.  \n  https://developer.penguin-stats.io/public-api
- **Penguin Statistics / ArkPlanner**  \n  Reference project for farming-planner concepts and Penguin planner
  interoperability. ArkPlanner is distributed under the MIT License.  \n  https://github.com/penguin-statistics/ArkPlanner

### Recommended external pull calculator
- **imivi / Arknights Pulls Calculator**  \n  Rhodes Planner does not include an internal pull calculator in v0.7.3. For pull-resource forecasting, this community tool is recommended as a separate companion utility.  \n  https://imivi.github.io/arknights-pulls-calculator/  \n  Source: https://github.com/imivi/arknights-pulls-calculator

### Account export ecosystem
- **ArkPRTS** by its community maintainers  \n  Users may generate account data outside Rhodes Planner and import the
  resulting JSON here. ArkPRTS is GPL-3.0 licensed. Rhodes Planner does not
  bundle or call ArkPRTS directly.  \n  https://github.com/ashleney/ArkPRTS
- **arkprtserver**  \n  Related account-data server/export tooling built on ArkPRTS, also GPL-3.0.
  Rhodes Planner only consumes a user-supplied export.  \n  https://github.com/ashleney/arkprtserver

### Community image sources
Operator/material images are requested from community-maintained image
repositories at runtime and are not bundled in the source release. Rhodes
Planner does not claim ownership of those assets or assume a license that the
upstream repositories do not clearly publish.
- https://github.com/PuppiizSunniiz/Arknight-Images
- https://github.com/Aceship/Arknight-Images

### Application libraries
Rhodes Planner is built with open-source Python tooling including **Streamlit,
Pydantic, pandas, requests, and platformdirs**. Their respective licenses and
notices remain with their maintainers.

### AI-assisted development
OpenAI's ChatGPT served as the primary AI-assisted development partner for prototyping, implementation, debugging, refactoring and testing. Product direction, requirements, validation, UX and release decisions were directed and reviewed by the project author.

### Thanks
Thanks to the Arknights community members who collect drop samples, maintain
game-data dumps, document account schemas, and keep utility projects alive.
Rhodes Planner would not be useful without that work.
        """
    )

# =====================================================================
# Dashboard
# =====================================================================
elif page == "Dashboard":
    st.subheader("Overview")
    future_count = sum(1 for meta in catalog.values() if not meta.get("available_on_en", True))

    imported_count = len(st.session_state.operators)
    depot_count = sum(
        1
        for iid in advancement_ids
        if st.session_state.inventory.materials.get(iid, 0) > 0
    )

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Operators in data", f"{len(catalog):,}")
    c2.metric("Account operators", f"{imported_count:,}")
    c3.metric("Depot materials", f"{depot_count:,}")
    c4.metric("Planned upgrades", f"{len(st.session_state.goals):,}")
    c5.metric("Crafting recipes", f"{len(recipes):,}")

    st.caption(f"Planner catalog: {len(catalog):,} latest-CN operators · {future_count:,} currently absent from the EN snapshot.")

    if imported_count or depot_count or st.session_state.goals:
        st.caption(
            "Your normalized profile is auto-saved locally. "
            "Close Rhodes Planner and come back later without re-importing."
        )

    st.markdown("### Workflow")
    st.info(
        "1. Import or edit account → 2. Plan upgrades → "
        "3. Reserve any stash you want to keep → "
        "4. Review crafting → 5. Farm what remains."
    )

# =====================================================================
# Account
# =====================================================================
elif page == "Account":
    st.subheader("Account state")

    st.markdown("#### Import ArkPRTS full data export")
    st.info(
        "Keep the raw ArkPRTS export private. Rhodes Planner stores only "
        "the normalized roster/depot/planning state, not the raw file."
    )

    ark_file = st.file_uploader(
        "ArkPRTS full data export (.json)",
        type=["json"],
        key="arkprts_upload",
    )

    if ark_file is not None and st.button(
        "Import ArkPRTS export",
        type="primary",
    ):
        try:
            if getattr(ark_file, "size", 0) > 25 * 1024 * 1024:
                raise ValueError("ArkPRTS export exceeds the 25 MB limit.")

            payload = json.load(ark_file)
            inv, ops, meta = parse_arkprts_full_export(payload)
            del payload

            # Data minimization: Rhodes keeps only inventory that can contribute
            # to operator progression plus EXP cards. Story/event collectibles and
            # gacha currencies are outside this toolkit's scope.
            allowed_inventory_ids = set(advancement_ids) | {
                "2001", "2002", "2003", "2004"
            }
            inv.materials = {
                iid: qty
                for iid, qty in inv.materials.items()
                if iid in allowed_inventory_ids
            }
            inv.exp_cards = {
                iid: int(inv.materials.get(iid, inv.exp_cards.get(iid, 0)) or 0)
                for iid in ("2001", "2002", "2003", "2004")
            }
            inv.exp = sum(
                inv.exp_cards.get(iid, 0) * value
                for iid, value in {
                    "2001": 200, "2002": 400, "2003": 1000, "2004": 2000
                }.items()
            )
            for cid, op in ops.items():
                if cid in catalog:
                    op.name = catalog[cid]["name"]
                    op.rarity = catalog[cid]["rarity"]

            st.session_state.inventory = inv
            st.session_state.operators = ops
            st.session_state.arkprts_meta = meta
            st.session_state.reserved_materials = set()
            bump_profile_epoch()
            persist_profile()
            st.success(
                f'Imported {len(ops)} operators and '
                f'{sum(1 for v in inv.materials.values() if v > 0)} '
                f'non-zero inventory entries. LMD/EXP and stash are committed.'
            )
            if st.session_state.goals:
                st.info(
                    "Existing upgrade goals were preserved. Review targets if "
                    "your operator progression changed since the plan was created."
                )

        except Exception as exc:
            st.error(f"ArkPRTS import failed: {exc}")

    if st.session_state.operators:
        operators = st.session_state.operators
        inv = st.session_state.inventory

        e2_count = sum(
            1 for op in operators.values()
            if op.elite == 2
        )
        m3_count = sum(
            int(op.mastery.s1 == 3)
            + int(op.mastery.s2 == 3)
            + int(op.mastery.s3 == 3)
            for op in operators.values()
        )

        a1, a2, a3, a4 = st.columns(4)
        a1.metric("Operators", f"{len(operators):,}")
        a2.metric("E2 operators", f"{e2_count:,}")
        a3.metric("M3 skills", f"{m3_count:,}")
        a4.metric(
            "Advancement materials owned",
            f"{sum(1 for iid in advancement_ids if inv.materials.get(iid, 0) > 0):,}",
        )

        b1, b2, b3 = st.columns(3)
        b1.metric("LMD", f"{inv.lmd:,}")
        b2.metric(
            "EXP stock · T3 equivalent",
            f"{inv.exp / 1000:,.1f}",
        )
        b3.metric(
            "EXP stock · T4 equivalent",
            f"{inv.exp / 2000:,.1f}",
        )

    st.divider()
    st.markdown("#### Manual operator state")
    st.caption(
        "Filter the roster and tick one row. The canonical Arknights "
        "classes are used: Vanguard, Guard, Defender, Sniper, Caster, "
        "Medic, Supporter and Specialist."
    )

    manual_cid = operator_selector_table(
        "account_operator",
        catalog,
        st.session_state.operators,
        owned_default=False,
    )

    if manual_cid:
        meta = catalog[manual_cid]
        manual_name = meta["name"]
        manual_rarity = meta["rarity"]

        existing = st.session_state.operators.get(
            manual_cid,
            OperatorState(
                operator_id=manual_cid,
                name=manual_name,
                rarity=manual_rarity,
            ),
        )

        st.markdown(f"**Editing:** {manual_name}")

        x1, x2, x3, x4 = st.columns(4)
        current_elite = x1.selectbox(
            "Elite",
            [0, 1, 2],
            index=existing.elite,
            key=f"manual_elite_{manual_cid}",
        )
        max_level = phase_max_level(
            constants,
            manual_rarity,
            current_elite,
        )
        current_level = x2.number_input(
            "Level",
            min_value=1,
            max_value=max_level,
            value=min(existing.level, max_level),
            key=f"manual_level_{manual_cid}",
        )
        current_skill = x3.selectbox(
            "Skill rank",
            list(range(1, 8)),
            index=existing.skill_level - 1,
            key=f"manual_skill_{manual_cid}",
        )
        current_potential = x4.selectbox(
            "Potential",
            list(range(1, 7)),
            index=min(existing.potential_rank, 5),
            key=f"manual_potential_{manual_cid}",
        )

        y1, y2, y3 = st.columns(3)
        current_s1 = y1.selectbox(
            "S1 mastery",
            [0, 1, 2, 3],
            index=existing.mastery.s1,
            key=f"manual_s1_{manual_cid}",
        )
        current_s2 = y2.selectbox(
            "S2 mastery",
            [0, 1, 2, 3],
            index=existing.mastery.s2,
            key=f"manual_s2_{manual_cid}",
        )
        current_s3 = y3.selectbox(
            "S3 mastery",
            [0, 1, 2, 3],
            index=existing.mastery.s3,
            key=f"manual_s3_{manual_cid}",
        )

        module_defs = module_catalog_for_operator(
            modules,
            manual_cid,
            en_modules,
        )
        module_levels = {}

        if module_defs:
            st.markdown("**Modules**")
            cols = st.columns(min(3, len(module_defs)))

            for idx, (module_id, module_def) in enumerate(
                module_defs.items()
            ):
                old_level = (
                    existing.modules[module_id].level
                    if module_id in existing.modules
                    else 0
                )

                module_levels[module_id] = cols[
                    idx % len(cols)
                ].selectbox(
                    module_def["name"],
                    [0, 1, 2, 3],
                    index=old_level,
                    key=f"manual_module_{manual_cid}_{module_id}",
                )

        if st.button(
            "Save manual operator state",
            key="save_manual_operator",
        ):
            module_states = dict(existing.modules)

            for module_id, level in module_levels.items():
                module_states[module_id] = ModuleProgress(
                    level=level,
                    locked=(level == 0),
                )

            st.session_state.operators[manual_cid] = OperatorState(
                operator_id=manual_cid,
                name=manual_name,
                rarity=manual_rarity,
                elite=current_elite,
                level=current_level,
                skill_level=current_skill,
                mastery=SkillState(
                    s1=current_s1,
                    s2=current_s2,
                    s3=current_s3,
                ),
                modules=module_states,
                potential_rank=current_potential - 1,
            )

            bump_profile_epoch()
            persist_profile()
            st.success(f"Saved {manual_name}.")

    st.divider()
    st.markdown("#### LMD & EXP cards")
    st.caption(
        "Changes are committed only when you press Save. Merely opening or "
        "refreshing the page can no longer overwrite imported resources."
    )

    inv = st.session_state.inventory
    epoch = int(st.session_state.get("profile_epoch", 0))

    with st.form(key=f"account_resources_form_{epoch}"):
        c1, c2, c3, c4, c5 = st.columns(5)

        form_lmd = c1.number_input(
            "LMD",
            min_value=0,
            value=int(inv.lmd),
            step=10000,
            key=f"account_lmd_{epoch}",
        )

        exp_labels = {
            "2001": "T1 · Drill",
            "2002": "T2 · Frontline",
            "2003": "T3 · Tactical",
            "2004": "T4 · Strategic",
        }
        form_cards = {}

        for col, iid in zip(
            [c2, c3, c4, c5],
            ["2001", "2002", "2003", "2004"],
        ):
            form_cards[iid] = col.number_input(
                exp_labels[iid],
                min_value=0,
                value=int(inv.exp_cards.get(iid, 0)),
                step=1,
                key=f"exp_card_{iid}_{epoch}",
            )

        form_exp = sum(
            int(form_cards[iid]) * EXP_VALUES[iid]
            for iid in EXP_VALUES
        )

        st.caption(
            f"Entered EXP stock = {form_exp / 1000:,.1f} T3 records "
            f"equivalent = {form_exp / 2000:,.1f} T4 records equivalent."
        )

        save_resources = st.form_submit_button(
            "Save LMD / EXP cards"
        )

    if save_resources:
        new_inv = st.session_state.inventory.model_copy(deep=True)
        new_inv.lmd = int(form_lmd)

        for iid, count in form_cards.items():
            new_inv.exp_cards[iid] = int(count)
            new_inv.materials[iid] = int(count)

        new_inv.exp = exp_from_cards(new_inv)
        st.session_state.inventory = new_inv
        bump_profile_epoch()
        persist_profile()
        st.success("LMD and EXP card stock saved.")

    st.markdown("#### Manual depot · advancement materials only")
    st.caption(
        "This list is derived from actual promotion, skill, mastery and "
        "module costs. Story/event collectibles that never upgrade an "
        "operator are excluded."
    )

    d1, d2 = st.columns([2, 1])
    depot_search = d1.text_input(
        "Search material",
        placeholder="Type a name...",
        key="depot_search",
    )
    depot_tiers = d2.multiselect(
        "Tier",
        [1, 2, 3, 4, 5],
        default=[1, 2, 3, 4, 5],
        key="depot_tiers",
    )

    current_inv = st.session_state.inventory
    depot_rows = []

    for iid in sorted(
        advancement_ids,
        key=lambda x: item_names.get(x, x).lower(),
    ):
        name = item_names.get(iid, iid)

        if depot_search and depot_search.lower() not in name.lower():
            continue

        tier = item_tier(
            item_meta.get(iid, {}).get("rarity")
        )

        if depot_tiers and tier not in depot_tiers:
            continue

        depot_rows.append({
            "Icon": item_icon_url(iid, item_meta),
            "Material": name,
            "Tier": tier,
            "Owned": int(current_inv.materials.get(iid, 0)),
            "Item ID": iid,
        })

    with st.form(key=f"depot_form_{epoch}"):
        edited_depot = st.data_editor(
            pd.DataFrame(depot_rows),
            use_container_width=True,
            hide_index=True,
            disabled=["Icon", "Material", "Tier", "Item ID"],
            column_config={
                "Icon": st.column_config.ImageColumn(
                    " ",
                    width="small",
                ),
                "Owned": st.column_config.NumberColumn(
                    "Owned",
                    min_value=0,
                    step=1,
                    format="%d",
                ),
                "Item ID": None,
            },
            key=f"manual_depot_table_{epoch}",
        )

        save_depot = st.form_submit_button(
            "Save visible depot changes"
        )

    if save_depot:
        new_inv = st.session_state.inventory.model_copy(deep=True)

        for _, row in edited_depot.iterrows():
            new_inv.materials[str(row["Item ID"])] = int(
                row["Owned"]
            )

        st.session_state.inventory = new_inv
        bump_profile_epoch()
        persist_profile()
        st.success("Depot changes saved.")

# =====================================================================
# Planner
# =====================================================================
elif page == "Planner":
    st.subheader("Upgrade Planner")
    st.caption(
        "Build targets from your real account state. Current progression is "
        "always treated as the minimum, so a plan can never downgrade an operator."
    )

    # -------------------------------------------------------------
    # Existing plan and actions
    # -------------------------------------------------------------
    if st.session_state.goals:
        st.markdown("### Current plan")

        plan_rows = []

        for goal in st.session_state.goals:
            current = goal["current"]
            target = goal["target"]
            module_text = ""

            if target.get("module_id"):
                module_current = (
                    current.get("modules", {})
                    .get(target["module_id"], {})
                    .get("level", 0)
                )
                module_name = str(
                    goal.get("module_name", target["module_id"])
                ).strip("'\"")
                module_text = (
                    f'{module_name} {module_current}→{target["module_level"]}'
                )

            plan_rows.append({
                "Portrait": operator_avatar_url(goal["operator_id"]),
                "Operator": goal["operator"],
                "From": f'E{current["elite"]} Lv{current["level"]}',
                "To": f'E{target["elite"]} Lv{target["level"]}',
                "Skill": f'{current["skill_level"]}→{target["skill_level"]}',
                "S1": f'{current["mastery"]["s1"]}→{target["mastery"]["s1"]}',
                "S2": f'{current["mastery"]["s2"]}→{target["mastery"]["s2"]}',
                "S3": f'{current["mastery"]["s3"]}→{target["mastery"]["s3"]}',
                "Module": module_text,
            })

        st.dataframe(
            pd.DataFrame(plan_rows),
            use_container_width=True,
            hide_index=True,
            column_config={
                "Portrait": st.column_config.ImageColumn(" ", width="small")
            },
        )

        st.markdown("#### Materials required by operator")
        st.caption("Exact progression requirements for each saved goal before stash/crafting reductions.")
        for goal, raw_cost in zip(st.session_state.goals, st.session_state.costs):
            bundle = CostBundle.model_validate(raw_cost)
            with st.container(border=True):
                c_op, c_goal = st.columns([2.2, 3.8])
                c_op.markdown(f'**{goal["operator"]}**')
                t = goal["target"]
                c_goal.caption(
                    f'E{t["elite"]} Lv{t["level"]} · Skill {t["skill_level"]} · '
                    f'S1 M{t["mastery"]["s1"]} / S2 M{t["mastery"]["s2"]} / S3 M{t["mastery"]["s3"]}'
                )
                render_cost_breakdown(bundle, item_meta, item_names)

        st.caption("Plan actions")
        for idx, goal in enumerate(st.session_state.goals):
            a1, a2, a3 = st.columns([5, 1.15, 1.15])
            a1.markdown(f'**{goal["operator"]}**')

            if a2.button(
                "✏️ Edit",
                key=f'edit_goal_{goal["operator_id"]}_{idx}',
                use_container_width=True,
            ):
                st.session_state.editing_goal_id = goal["operator_id"]
                st.session_state.edit_epoch = int(
                    st.session_state.get("edit_epoch", 0)
                ) + 1
                st.rerun()

            if a3.button(
                "🗑 Remove",
                key=f'remove_goal_{goal["operator_id"]}_{idx}',
                use_container_width=True,
            ):
                st.session_state.goals.pop(idx)
                if idx < len(st.session_state.costs):
                    st.session_state.costs.pop(idx)
                if st.session_state.get("editing_goal_id") == goal["operator_id"]:
                    st.session_state.editing_goal_id = None
                persist_profile()
                st.rerun()

        if st.button("Clear all goals"):
            st.session_state.goals = []
            st.session_state.costs = []
            st.session_state.editing_goal_id = None
            persist_profile()
            st.rerun()

        st.divider()

    # -------------------------------------------------------------
    # Select a new operator, or open an existing goal for editing.
    # -------------------------------------------------------------
    editing_goal_id = st.session_state.get("editing_goal_id")
    editing_goal = next(
        (
            g for g in st.session_state.goals
            if g.get("operator_id") == editing_goal_id
        ),
        None,
    )

    if editing_goal:
        cid = editing_goal["operator_id"]
        st.info(
            f'Editing **{editing_goal["operator"]}**. Update the target below and save.'
        )
        if st.button("Cancel edit"):
            st.session_state.editing_goal_id = None
            st.session_state.edit_epoch = int(
                st.session_state.get("edit_epoch", 0)
            ) + 1
            st.rerun()
    else:
        st.markdown("### Add an operator")
        st.caption(
            "Filter by name, class, rarity, or ownership, then tick one operator. "
        "The catalog uses the latest CN data, so CN-only operators can be pre-planned."
        )
        cid = operator_selector_table(
            "planner_operator",
            catalog,
            st.session_state.operators,
            owned_default=False,
        )

    if cid:
        selected = catalog[cid]
        selected_name = selected["name"]
        rarity = selected["rarity"]

        existing = st.session_state.operators.get(
            cid,
            OperatorState(
                operator_id=cid,
                name=selected_name,
                rarity=rarity,
            ),
        )

        saved_target = (
            editing_goal.get("target", {})
            if editing_goal and editing_goal.get("operator_id") == cid
            else {}
        )
        saved_module_id = saved_target.get("module_id") or ""

        account_source = (
            "Current state loaded from your local account profile"
            if cid in st.session_state.operators
            else "Not owned · planning starts from E0 Lv1"
        )

        safe_name = html.escape(str(selected_name))
        safe_class = html.escape(str(selected.get("class", "")))
        safe_source = html.escape(account_source)
        availability = html.escape(str(selected.get("availability", "EN")))

        st.markdown(
            f"""
            <div class="operator-card">
                {avatar_html(cid, 92)}
                <div>
                    <div class="operator-title">{safe_name}</div>
                    <div class="operator-sub">
                        {"★" * rarity} · {safe_class}
                    </div>
                    <div class="operator-sub">{safe_source} · {availability}</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown("### Current state")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Elite", f"E{existing.elite}")
        c2.metric("Level", existing.level)
        c3.metric("Skill rank", existing.skill_level)
        c4.metric("Potential", existing.potential_rank + 1)

        m1, m2, m3 = st.columns(3)
        m1.metric("S1 mastery", existing.mastery.s1)
        m2.metric("S2 mastery", existing.mastery.s2)
        m3.metric("S3 mastery", existing.mastery.s3)

        module_defs = module_catalog_for_operator(modules, cid, en_modules)

        if module_defs:
            current_module_text = []
            for module_id, module_def in module_defs.items():
                level = (
                    existing.modules[module_id].level
                    if module_id in existing.modules
                    else 0
                )
                module_name = str(module_def["name"]).strip("'\"")
                current_module_text.append(f"{module_name}: Lv{level}")
            st.caption("Modules · " + " | ".join(current_module_text))

        st.caption("Current state is read-only here. Edit it from Account if needed.")
        st.markdown("### Target")

        widget_epoch = int(st.session_state.get("edit_epoch", 0))
        widget_suffix = f"{cid}_{widget_epoch}"

        elite_options = list(range(existing.elite, 3))
        saved_elite = int(saved_target.get("elite", 2 if 2 in elite_options else existing.elite))
        saved_elite = max(existing.elite, min(2, saved_elite))
        if saved_elite not in elite_options:
            saved_elite = elite_options[-1]

        target_elite = st.selectbox(
            "Target Elite",
            elite_options,
            index=elite_options.index(saved_elite),
            key=f"target_elite_{widget_suffix}",
        )

        max_target_level = phase_max_level(constants, rarity, target_elite)
        min_target_level = existing.level if target_elite == existing.elite else 1
        default_level = int(saved_target.get(
            "level",
            max(existing.level, 60) if target_elite == 2 else min_target_level,
        ))
        default_level = min(max_target_level, max(min_target_level, default_level))

        t1, t2 = st.columns(2)
        target_level = t1.number_input(
            "Target level",
            min_value=min_target_level,
            max_value=max_target_level,
            value=default_level,
            key=f"target_level_{widget_suffix}_{target_elite}",
        )

        skill_options = list(range(existing.skill_level, 8))
        default_skill = int(saved_target.get("skill_level", skill_options[-1]))
        default_skill = max(existing.skill_level, min(7, default_skill))
        target_skill = t2.selectbox(
            "Target skill rank",
            skill_options,
            index=skill_options.index(default_skill),
            key=f"target_skill_{widget_suffix}",
        )

        saved_mastery = saved_target.get("mastery", {})
        q1, q2, q3 = st.columns(3)

        s1_options = list(range(existing.mastery.s1, 4))
        s2_options = list(range(existing.mastery.s2, 4))
        s3_options = list(range(existing.mastery.s3, 4))

        default_s1 = max(existing.mastery.s1, min(3, int(saved_mastery.get("s1", existing.mastery.s1))))
        default_s2 = max(existing.mastery.s2, min(3, int(saved_mastery.get("s2", existing.mastery.s2))))
        default_s3 = max(existing.mastery.s3, min(3, int(saved_mastery.get("s3", s3_options[-1]))))

        target_s1 = q1.selectbox(
            "S1 mastery", s1_options,
            index=s1_options.index(default_s1),
            key=f"target_s1_{widget_suffix}",
        )
        target_s2 = q2.selectbox(
            "S2 mastery", s2_options,
            index=s2_options.index(default_s2),
            key=f"target_s2_{widget_suffix}",
        )
        target_s3 = q3.selectbox(
            "S3 mastery", s3_options,
            index=s3_options.index(default_s3),
            key=f"target_s3_{widget_suffix}",
        )

        target_module_id = None
        target_module_level = 0

        if module_defs:
            st.markdown("#### Module target")
            module_options = [""] + list(module_defs)
            if saved_module_id not in module_options:
                saved_module_id = ""

            target_module_id = st.selectbox(
                "Module",
                module_options,
                index=module_options.index(saved_module_id),
                format_func=lambda mid: (
                    "No module upgrade"
                    if not mid
                    else str(module_defs[mid]["name"]).strip("'\"")
                ),
                key=f"target_module_{widget_suffix}",
            )

            if target_module_id:
                current_module_level = (
                    existing.modules[target_module_id].level
                    if target_module_id in existing.modules
                    else 0
                )
                levels = list(range(current_module_level, 4))
                default_module_level = int(saved_target.get("module_level", levels[-1]))
                default_module_level = max(current_module_level, min(3, default_module_level))

                z1, z2 = st.columns(2)
                z1.metric("Current module level", current_module_level)
                target_module_level = z2.selectbox(
                    "Target module level",
                    levels,
                    index=levels.index(default_module_level),
                    key=f"target_module_level_{widget_suffix}_{target_module_id}",
                )

        save_label = "💾 Save changes" if editing_goal else "➕ Add to plan"

        if st.button(save_label, type="primary"):
            try:
                target = UpgradeGoal(
                    operator_id=cid,
                    elite=target_elite,
                    level=target_level,
                    skill_level=target_skill,
                    mastery=SkillState(
                        s1=target_s1,
                        s2=target_s2,
                        s3=target_s3,
                    ),
                    module_id=target_module_id or None,
                    module_level=target_module_level,
                )

                model = build_operator_cost_model(cid, chars, modules, en_modules)
                cost = calculate_upgrade_cost(
                    current=existing,
                    target=target,
                    model=model,
                    constants=constants,
                    leveling_fn=leveling_cost,
                )

                goal = {
                    "operator": selected_name,
                    "operator_id": cid,
                    "current": existing.model_dump(),
                    "target": target.model_dump(),
                    "module_name": (
                        str(module_defs[target_module_id]["name"]).strip("'\"")
                        if target_module_id
                        else ""
                    ),
                }

                existing_idx = next(
                    (
                        i for i, g in enumerate(st.session_state.goals)
                        if g.get("operator_id") == cid
                    ),
                    None,
                )

                if existing_idx is None:
                    st.session_state.goals.append(goal)
                    st.session_state.costs.append(cost.model_dump())
                else:
                    st.session_state.goals[existing_idx] = goal
                    st.session_state.costs[existing_idx] = cost.model_dump()

                st.session_state.editing_goal_id = None
                st.session_state.edit_epoch = int(
                    st.session_state.get("edit_epoch", 0)
                ) + 1
                persist_profile()
                st.session_state["_flash_message"] = (
                    f"Saved upgrade plan for {selected_name}."
                )
                st.rerun()

            except Exception as exc:
                st.error(str(exc))

# =====================================================================
# Farming
# =====================================================================
elif page == "Farming":
    st.subheader("Farm Plan")
    st.caption(
        "See what your stash covers, what should be crafted, and the stages "
        "needed for everything that remains."
    )

    if not st.session_state.costs:
        st.info("Add at least one upgrade goal first.")

    else:
        costs = [
            CostBundle.model_validate(x)
            for x in st.session_state.costs
        ]
        total = aggregate_costs(costs)
        inv = st.session_state.inventory

        req_tab, craft_tab, stage_tab = st.tabs(
            ["Requirements", "Crafting", "Stages"]
        )

        with req_tab:
            st.markdown("### Requirements by operator")
            st.caption("See which operator creates each material requirement before Rhodes combines the plan.")
            for goal, bundle in zip(st.session_state.goals, costs):
                with st.container(border=True):
                    st.markdown(f'**{goal["operator"]}**')
                    render_cost_breakdown(bundle, item_meta, item_names)

            st.markdown("### Combined total requirements")
            render_cost_breakdown(total, item_meta, item_names)
            st.caption("The editable table below is the same combined total, with stash and availability context added.")

            st.markdown("### Resource policy")
            st.caption(
                "Reserve stash means: do not spend what I already own. For a "
                "reserved T4/T5 material, Rhodes also ignores owned crafting "
                "components and farms the full ingredient chain from T3 upward."
            )

            r1, r2 = st.columns(2)

            farm_full_lmd = r1.checkbox(
                "Reserve my current LMD",
                value=bool(
                    st.session_state.get(
                        "farm_full_lmd",
                        False,
                    )
                ),
                key="farm_full_lmd",
            )
            farm_full_exp = r2.checkbox(
                "Reserve my current EXP cards",
                value=bool(
                    st.session_state.get(
                        "farm_full_exp",
                        False,
                    )
                ),
                key="farm_full_exp",
            )

            before_craft = calculate_deficit(
                total,
                inv,
                reserved_materials=(
                    st.session_state.reserved_materials
                ),
                farm_full_lmd=farm_full_lmd,
                farm_full_exp=farm_full_exp,
            )

            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Required LMD", f"{total.lmd:,}")
            m2.metric(
                "LMD to cover",
                f"{before_craft.lmd:,}",
            )
            m3.metric(
                "Required EXP · T3 equiv.",
                f"{total.exp / 1000:,.1f}",
                help=f"{total.exp / 2000:,.1f} T4 equivalent",
            )
            m4.metric(
                "EXP to cover · T3 equiv.",
                f"{before_craft.exp / 1000:,.1f}",
                help=f"{before_craft.exp / 2000:,.1f} T4 equivalent",
            )

            requirement_rows = []

            for iid, qty in sorted(
                total.materials.items(),
                key=lambda kv: item_names.get(
                    kv[0],
                    kv[0],
                ).lower(),
            ):
                owned_qty = inv.materials.get(iid, 0)
                reserve = (
                    iid
                    in st.session_state.reserved_materials
                )

                requirement_rows.append({
                    "Reserve stash": reserve,
                    "Icon": item_icon_url(
                        iid,
                        item_meta,
                    ),
                    "Item": item_names.get(iid, iid),
                    "Required": qty,
                    "Owned": owned_qty,
                    "Availability": ("EN" if iid in en_item_meta else "CN only / future EN"),
                    "Need before crafting": (
                        qty
                        if reserve
                        else max(0, qty - owned_qty)
                    ),
                    "Item ID": iid,
                })

            edited = st.data_editor(
                pd.DataFrame(requirement_rows),
                use_container_width=True,
                hide_index=True,
                disabled=[
                    "Icon",
                    "Item",
                    "Required",
                    "Owned",
                    "Availability",
                    "Need before crafting",
                    "Item ID",
                ],
                column_config={
                    "Reserve stash": (
                        st.column_config.CheckboxColumn(
                            "Reserve stash"
                        )
                    ),
                    "Icon": st.column_config.ImageColumn(
                        " ",
                        width="small",
                    ),
                    "Item ID": None,
                },
                key="reserve_material_editor",
            )

            st.session_state.reserved_materials = set(
                edited.loc[
                    edited["Reserve stash"] == True,
                    "Item ID",
                ].astype(str)
            )

        reserved_ids = set(st.session_state.reserved_materials)
        normal_required = {
            iid: qty
            for iid, qty in total.materials.items()
            if iid not in reserved_ids
        }
        reserved_required = {
            iid: qty
            for iid, qty in total.materials.items()
            if iid in reserved_ids
        }

        # Normal requirements may consume the depot and craft from owned parts.
        craft_result = simulate_crafting(
            required=normal_required,
            owned=inv.materials,
            recipes=recipes,
            reserved_items=set(),
        )

        normal_expansion = expand_high_tier_farm_targets(
            remaining=craft_result["remaining"],
            stock_after=craft_result["stock_after"],
            recipes=recipes,
            item_meta=item_meta,
            stop_tier=3,
        )

        # Reserved requirements deliberately ignore both the owned output and
        # the owned ingredient chain. The full chain is obtained anew.
        reserved_expansion = expand_reserved_requirements(
            required=reserved_required,
            recipes=recipes,
            item_meta=item_meta,
            stop_tier=3,
        )

        farm_expansion = merge_farm_expansions(
            normal_expansion,
            reserved_expansion,
        )

        gross_lmd_required = (
            total.lmd
            + craft_result["lmd_crafting"]
            + farm_expansion["lmd_crafting"]
        )

        lmd_before_base = (
            gross_lmd_required
            if farm_full_lmd
            else max(
                0,
                gross_lmd_required - inv.lmd,
            )
        )

        exp_before_base = (
            total.exp
            if farm_full_exp
            else max(0, total.exp - inv.exp)
        )

        with craft_tab:
            st.markdown("### What your current stash can cover")
            if reserved_required:
                st.caption(
                    "Reserved materials are excluded from stash coverage. Their "
                    "required crafting inputs are planned as newly farmed resources."
                )

            craft_rows = []

            for row in craft_result["item_rows"]:
                iid = row["item_id"]

                craft_rows.append({
                    "Icon": item_icon_url(
                        iid,
                        item_meta,
                    ),
                    "Item": item_names.get(iid, iid),
                    "Required": row["required"],
                    "From stash": row["from_stash"],
                    "Craftable now": row["crafted"],
                    "Still missing": row["remaining"],
                    "Stash reserved": row["reserved"],
                })

            st.dataframe(
                pd.DataFrame(craft_rows),
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Icon": st.column_config.ImageColumn(
                        " ",
                        width="small",
                    )
                },
            )

            st.markdown("### Craft now")

            if craft_result["craft_ops"]:
                rows = []

                for op in craft_result["craft_ops"]:
                    consumes = ", ".join(
                        f'{item_names.get(iid, iid)} '
                        f'×{fmt_num(qty)}'
                        for iid, qty
                        in op["ingredients"].items()
                    )

                    rows.append({
                        "Craft": item_names.get(
                            op["output_id"],
                            op["output_id"],
                        ),
                        "Batches": op["batches"],
                        "Output": op["output_quantity"],
                        "Consumes": consumes,
                        "LMD cost": op["lmd_cost"],
                    })

                st.dataframe(
                    pd.DataFrame(rows),
                    use_container_width=True,
                    hide_index=True,
                )
            else:
                st.info(
                    "Nothing can or needs to be crafted immediately "
                    "from the current stash."
                )

            st.markdown("### Farm T3 inputs, then craft upward")

            if farm_expansion["future_craft_ops"]:
                rows = []

                for op in farm_expansion[
                    "future_craft_ops"
                ]:
                    consumes = ", ".join(
                        f'{item_names.get(iid, iid)} '
                        f'×{fmt_num(qty)}'
                        for iid, qty
                        in op["ingredients"].items()
                    )

                    rows.append({
                        "Craft after farming": (
                            item_names.get(
                                op["output_id"],
                                op["output_id"],
                            )
                        ),
                        "Batches": op["batches"],
                        "Output": op["output_quantity"],
                        "Inputs": consumes,
                        "LMD cost": op["lmd_cost"],
                    })

                st.dataframe(
                    pd.DataFrame(rows),
                    use_container_width=True,
                    hide_index=True,
                )
            else:
                st.info(
                    "No future high-tier crafting is required."
                )

            st.metric(
                "Workshop LMD cost",
                (
                    craft_result["lmd_crafting"]
                    + farm_expansion["lmd_crafting"]
                ),
            )

        with stage_tab:
            st.markdown("### Passive base production")

            p1, p2, p3 = st.columns(3)

            planning_days = p1.number_input(
                "Planning horizon (days)",
                min_value=0.0,
                value=float(
                    st.session_state.get(
                        "planning_days",
                        7.0,
                    )
                ),
                step=1.0,
                key="planning_days",
            )
            base_lmd_per_day = p2.number_input(
                "Base LMD / day",
                min_value=0,
                value=int(
                    st.session_state.get(
                        "base_lmd_per_day",
                        0,
                    )
                ),
                step=1000,
                key="base_lmd_per_day",
            )
            base_t3_per_day = p3.number_input(
                "Base T3 Tactical Battle Records / day",
                min_value=0,
                value=int(
                    st.session_state.get(
                        "base_t3_per_day",
                        0,
                    )
                ),
                step=1,
                key="base_t3_per_day",
                help=(
                    "1 T3 Tactical Battle Record = 1,000 EXP."
                ),
            )

            passive_lmd = min(
                lmd_before_base,
                int(base_lmd_per_day * planning_days),
            )
            passive_exp = min(
                exp_before_base,
                int(
                    base_t3_per_day
                    * 1000
                    * planning_days
                ),
            )

            lmd_to_farm = max(
                0,
                lmd_before_base - passive_lmd,
            )
            exp_to_farm = max(
                0,
                exp_before_base - passive_exp,
            )

            final_deficit = CostBundle(
                lmd=lmd_to_farm,
                exp=exp_to_farm,
                materials=(
                    farm_expansion["farm_targets"]
                ),
            )

            st.markdown("### Remaining resources to farm")

            f1, f2, f3, f4 = st.columns(4)
            f1.metric(
                "LMD before base",
                f"{lmd_before_base:,}",
            )
            f2.metric(
                "LMD after base",
                f"{lmd_to_farm:,}",
            )
            f3.metric(
                "EXP before base · T3 equiv.",
                f"{exp_before_base / 1000:,.1f}",
                help=(
                    f"{exp_before_base / 2000:,.1f} "
                    f"T4 equivalent"
                ),
            )
            f4.metric(
                "EXP after base · T3 equiv.",
                f"{exp_to_farm / 1000:,.1f}",
                help=(
                    f"{exp_to_farm / 2000:,.1f} "
                    f"T4 equivalent"
                ),
            )

            farm = build_farming_plan(
                final_deficit,
                stages,
            )

            unavailable_targets = {
                iid: qty for iid, qty in final_deficit.materials.items()
                if qty > 0 and best_stage_for_item(iid, stages) is None
            }
            if unavailable_targets:
                st.warning(
                    "Some required materials have no farming source in the selected "
                    "Penguin server dataset yet. This is expected for future/CN-only "
                    "content; the requirement is preserved rather than guessed."
                )
                st.dataframe(pd.DataFrame([
                    {
                        "Material": item_names.get(iid, iid),
                        "Required to farm": qty,
                        "Availability": ("CN only / future EN" if iid not in en_item_meta else "Farming data pending"),
                    }
                    for iid, qty in sorted(unavailable_targets.items(), key=lambda kv: item_names.get(kv[0], kv[0]).lower())
                ]), use_container_width=True, hide_index=True)

            if not stages and not is_demo:
                st.warning(
                    "Live drop statistics are unavailable, "
                    "so stage recommendations are disabled."
                )

            elif farm.lines:
                farm_rows = []

                for line in farm.lines:
                    if line.purpose == "LMD":
                        purpose = "LMD"
                    elif line.purpose == "EXP":
                        purpose = "EXP"
                    else:
                        purpose = item_names.get(
                            line.purpose,
                            line.purpose,
                        )

                    if (
                        line.purpose == "EXP"
                        and line.stage_code == "LS-6"
                    ):
                        expected = (
                            f"{line.runs * 4} T4 + "
                            f"{line.runs * 2} T3"
                        )
                    elif line.purpose == "EXP":
                        expected = (
                            f"{line.expected_output / 1000:,.1f} "
                            f"T3 equiv."
                        )
                    else:
                        expected = round(
                            line.expected_output,
                            2,
                        )

                    farm_rows.append({
                        "Stage": line.stage_code,
                        "Purpose": purpose,
                        "Runs": line.runs,
                        "Sanity": line.sanity,
                        "Expected output": expected,
                    })

                st.dataframe(
                    pd.DataFrame(farm_rows),
                    use_container_width=True,
                    hide_index=True,
                )

                ce_line = next(
                    (
                        x for x in farm.lines
                        if x.purpose == "LMD"
                    ),
                    None,
                )
                ls_line = next(
                    (
                        x for x in farm.lines
                        if x.purpose == "EXP"
                    ),
                    None,
                )

                e1, e2, e3 = st.columns(3)

                e1.metric(
                    "Pure LMD stage runs",
                    (
                        f"{ce_line.stage_code} × "
                        f"{ce_line.runs}"
                        if ce_line else "0"
                    ),
                )

                exp_help = None
                if (
                    ls_line
                    and ls_line.stage_code == "LS-6"
                ):
                    exp_help = (
                        f"Produces {ls_line.runs * 4} T4 "
                        f"+ {ls_line.runs * 2} T3 records"
                    )

                e2.metric(
                    "Pure EXP stage runs",
                    (
                        f"{ls_line.stage_code} × "
                        f"{ls_line.runs}"
                        if ls_line else "0"
                    ),
                    help=exp_help,
                )

                e3.metric(
                    "Total sanity",
                    f"{farm.total_sanity:,}",
                )

                st.caption(
                    f"Passive credit over {planning_days:g} day(s): "
                    f"{passive_lmd:,} LMD + "
                    f"{passive_exp / 1000:,.1f} T3 records equivalent."
                )

            else:
                st.success(
                    "Nothing remains to farm with the selected policy."
                )

            st.markdown("### Send to Penguin Statistics")
            st.caption(
                "Copy the effective farming config, then paste it into Penguin "
                "Statistics. Rhodes exports the same remaining farm targets shown "
                "above after reserve rules, crafting expansion, stash use and base "
                "production. This prevents Penguin from subtracting your depot a "
                "second time."
            )

            penguin_json = build_penguin_planner_config_json(
                inventory=inv,
                farm_targets=farm_expansion["farm_targets"],
                additional_lmd=lmd_to_farm,
                additional_exp=exp_to_farm,
                item_meta=item_meta,
            )

            clipboard_button(
                penguin_json,
                label="Copy Penguin Statistics config",
            )

            with st.expander("Preview config"):
                st.code(penguin_json, language="json")
                st.caption(
                    "Format: @penguin-statistics/planner/config with id / need / have. "
                    "`need` is adjusted so Penguin sees the same incremental farm targets as Rhodes. "
                    "Operator EXP is represented as a T4-first Battle Record mix."
                )

            # Safe auto-save for planner preferences. Only the Farming page is
            # rendered here; Account input widgets are not involved.
            persist_profile()

# =====================================================================
# About
# =====================================================================
elif page == "About":
    st.subheader(f"About this build · v{__version__}")

    st.markdown(
        """
### Data flow

**ArkPRTS/manual account state**  
→ **persistent local profile**  
→ **hard current-state floor**  
→ **operator upgrade goals**  
→ **requirements + stash policy**  
→ **craft now**  
→ **T3-first future farming/crafting**  
→ **passive base production**  
→ **stage recommendations**

The progression knowledge base uses latest CN data; the EN snapshot is used for localization/availability, while Penguin server selection controls current farming recommendations.

### Local persistence

Rhodes Planner auto-saves the normalized roster, depot, upgrade plans and
planner settings into your Windows user application-data folder. The raw
ArkPRTS export is not persisted by Rhodes Planner. Use the **Nuke / clear local
profile** button in the sidebar to delete the saved profile.

### EXP convention

- T3 Tactical Battle Record = **1,000 EXP**
- T4 Strategic Battle Record = **2,000 EXP**
- LS-6 is shown in tangible card output: **4 T4 + 2 T3 per run**

### Export

- **Penguin Statistics Planner config** uses the
  `@penguin-statistics/planner/config` shape with `id`, `need`, and `have`
  fields, matching the user-provided Penguin export example.
- Excel export has been removed from Rhodes Planner.

### Security

The local launcher binds Rhodes Planner to `127.0.0.1`. The persisted profile
contains normalized roster/depot/planning data and is **not encrypted at rest**.
See `SECURITY.md` for the full threat model.
"""
    )

