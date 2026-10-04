from __future__ import annotations
from typing import Any, Dict

from .http import get_json
from rhodes.core.models import CostBundle, OperatorCostModel

REGION_BASES = {
    "EN": "https://raw.githubusercontent.com/ArknightsAssets/ArknightsGamedata/master/en/gamedata/excel",
    "CN": "https://raw.githubusercontent.com/ArknightsAssets/ArknightsGamedata/master/cn/gamedata/excel",
}

# Secondary CN snapshot used only if the primary community mirror is temporarily
# unavailable. Rhodes never bundles these datasets.
CN_FALLBACK_BASE = "https://raw.githubusercontent.com/Kengxxiao/ArknightsGameData/master/zh_CN/gamedata/excel"


# Community English display aliases for CN-only progression materials that do
# not yet have an official EN game-data entry. These are display-only aliases;
# item IDs and all progression/crafting logic continue to come from game data.
# Keep this map small and evidence-based.
COMMUNITY_EN_ITEM_ALIASES = {
    "电极单元": "Electrode Unit",
    "液化高能气体": "Liquefied High-Energy Gas",
    "液化醚吸聚体": "Liquefied Ether Agglomerate",
    "聚能动力单元": "Concentrated Power Unit",
}


def _community_item_alias(name: str) -> str:
    return COMMUNITY_EN_ITEM_ALIASES.get(str(name or ""), str(name or ""))


def _region_urls(region: str):
    base = REGION_BASES[region]
    return {
        "characters": f"{base}/character_table.json",
        "items": f"{base}/item_table.json",
        "constants": f"{base}/gamedata_const.json",
        "modules": f"{base}/uniequip_table.json",
        "stages": f"{base}/stage_table.json",
        "building": f"{base}/building_data.json",
    }


def _cost_list_to_bundle(rows) -> CostBundle:
    out = CostBundle()
    if not rows:
        return out

    for x in rows:
        if not isinstance(x, dict):
            continue

        item_id = str(x.get("id") or x.get("itemId") or "")
        count = x.get("count", x.get("amount", 0)) or 0
        item_type = str(x.get("type") or "").upper()

        if not item_id:
            continue

        if item_id == "4001" or item_type == "GOLD":
            out.lmd += int(count)
        else:
            out.materials[item_id] = out.materials.get(item_id, 0) + float(count)

    return out


def _unwrap_items(raw: Any) -> Dict[str, Any]:
    if isinstance(raw, dict) and "items" in raw and isinstance(raw["items"], dict):
        return raw["items"]
    if isinstance(raw, dict):
        return raw
    return {}


def _parse_rarity(raw_rarity) -> int:
    if raw_rarity is None:
        return 1

    if isinstance(raw_rarity, str):
        value = raw_rarity.strip().upper()
        if value.startswith("TIER_"):
            try:
                return max(1, min(6, int(value.split("_", 1)[1])))
            except (TypeError, ValueError):
                return 1
        try:
            n = int(value)
            return n + 1 if 0 <= n <= 5 else max(1, min(6, n))
        except ValueError:
            return 1

    if isinstance(raw_rarity, (int, float)):
        n = int(raw_rarity)
        return n + 1 if 0 <= n <= 5 else max(1, min(6, n))

    return 1



CANONICAL_PROFESSIONS = {
    "PIONEER": "Vanguard",
    "WARRIOR": "Guard",
    "TANK": "Defender",
    "SNIPER": "Sniper",
    "CASTER": "Caster",
    "MEDIC": "Medic",
    "SUPPORT": "Supporter",
    "SPECIAL": "Specialist",
}


def profession_label(raw_profession: str) -> str:
    value = str(raw_profession or "").upper()
    return CANONICAL_PROFESSIONS.get(value, str(raw_profession or "").title())


def _collect_cost_item_ids(rows, output: set[str]) -> None:
    if not isinstance(rows, list):
        return

    for row in rows:
        if not isinstance(row, dict):
            continue

        iid = str(row.get("id") or row.get("itemId") or "")
        if iid and iid not in {"4001", "2001", "2002", "2003", "2004"}:
            output.add(iid)


def advancement_item_ids(characters_raw, modules_raw, item_meta) -> set[str]:
    ids: set[str] = set()

    for row in (characters_raw or {}).values():
        if not isinstance(row, dict):
            continue

        profession = str(row.get("profession") or "").upper()
        if profession not in CANONICAL_PROFESSIONS:
            continue

        for phase in row.get("phases") or []:
            if isinstance(phase, dict):
                _collect_cost_item_ids(phase.get("evolveCost"), ids)

        for cond in row.get("allSkillLvlup") or []:
            if isinstance(cond, dict):
                _collect_cost_item_ids(
                    cond.get("lvlUpCost") or cond.get("levelUpCost"),
                    ids,
                )

        for skill in row.get("skills") or []:
            if not isinstance(skill, dict):
                continue
            for cond in skill.get("levelUpCostCond") or []:
                if isinstance(cond, dict):
                    _collect_cost_item_ids(
                        cond.get("levelUpCost") or cond.get("lvlUpCost"),
                        ids,
                    )

    if isinstance(modules_raw, dict):
        equip_dict = modules_raw.get("equipDict", {})
        if isinstance(equip_dict, dict):
            for module in equip_dict.values():
                if not isinstance(module, dict):
                    continue

                item_cost = module.get("itemCost") or {}

                if isinstance(item_cost, dict):
                    cost_sets = item_cost.values()
                elif isinstance(item_cost, list):
                    cost_sets = item_cost
                else:
                    cost_sets = []

                for rows in cost_sets:
                    _collect_cost_item_ids(rows, ids)

    filtered = set()

    for iid in ids:
        tier = _parse_rarity(
            item_meta.get(iid, {}).get("rarity")
        )
        if 1 <= tier <= 5:
            filtered.add(iid)

    # Dualchips are manufactured from Chip Packs + Chip Catalyst. Chip Catalyst
    # is not a direct operator-cost item, so include it explicitly in the
    # editable depot when it exists in the current game-data snapshot.
    for iid, meta in (item_meta or {}).items():
        if str((meta or {}).get("name") or "").strip().casefold() == "chip catalyst":
            filtered.add(str(iid))

    return filtered


def _fetch_region(region: str):
    region = str(region).upper()
    urls = _region_urls(region)

    def fetch(name: str, hours: int = 24):
        try:
            return get_json(urls[name], f"{region.lower()}_{name}", hours)
        except Exception:
            if region != "CN":
                raise
            fallback = f"{CN_FALLBACK_BASE}/{urls[name].rsplit('/', 1)[-1]}"
            return get_json(fallback, f"cn_fallback_{name}", hours)

    characters = fetch("characters")
    items = fetch("items")
    constants = fetch("constants")
    modules = fetch("modules")
    stages = fetch("stages")
    try:
        building = fetch("building")
    except Exception:
        building = {}
    return characters, items, constants, modules, stages, building


def fetch_game_data():
    """Return a CN-complete planning snapshot plus current EN availability data.

    CN is the planner knowledge base so Global/EN users can pre-plan operators,
    materials and crafting chains before release. EN remains an availability
    reference and is not used to truncate the planner catalog. Only the EN
    tables needed for localization/availability are fetched.
    """
    cn = _fetch_region("CN")
    en_urls = _region_urls("EN")
    en_characters = get_json(en_urls["characters"], "en_characters", 24)
    en_items = get_json(en_urls["items"], "en_items", 24)
    en_modules = get_json(en_urls["modules"], "en_modules", 24)
    en_stages = get_json(en_urls["stages"], "en_stages", 24)
    return (*cn, en_characters, en_items, en_modules, en_stages)


def build_item_metadata_map(items_raw, localized_items_raw=None) -> Dict[str, dict]:
    items = _unwrap_items(items_raw)
    localized = _unwrap_items(localized_items_raw) if localized_items_raw is not None else {}
    out = {}

    for iid, row in items.items():
        if not isinstance(row, dict):
            continue

        local_row = localized.get(str(iid), {}) if isinstance(localized, dict) else {}
        out[str(iid)] = {
            "id": str(iid),
            "name": str(local_row.get("name") or _community_item_alias(row.get("name")) or iid),
            "cn_name": str(row.get("name") or iid),
            "icon_id": str(local_row.get("iconId") or row.get("iconId") or iid),
            "rarity": row.get("rarity"),
            "item_type": row.get("itemType"),
            "classify_type": row.get("classifyType"),
        }

    return out


def build_item_name_map(items_raw) -> Dict[str, str]:
    return {
        iid: meta["name"]
        for iid, meta in build_item_metadata_map(items_raw).items()
    }


def operator_catalog(characters_raw, en_characters_raw=None) -> Dict[str, dict]:
    out = {}

    for cid, row in (characters_raw or {}).items():
        if not isinstance(row, dict):
            continue

        name = row.get("name")
        profession = str(row.get("profession") or "").upper()

        if not name or not str(cid).startswith("char_"):
            continue
        if profession not in CANONICAL_PROFESSIONS:
            continue

        rarity = _parse_rarity(row.get("rarity"))

        en_row = (en_characters_raw or {}).get(cid) if isinstance(en_characters_raw, dict) else None
        display_name = (en_row or {}).get("name") or row.get("appellation") or name
        out[cid] = {
            "id": cid,
            "name": display_name,
            "cn_name": name,
            "rarity": max(1, min(6, rarity)),
            "profession": profession,
            "class": profession_label(profession),
            "availability": "EN" if isinstance(en_row, dict) else "CN only",
            "available_on_en": isinstance(en_row, dict),
        }

    return out


def phase_max_level(constants: dict, rarity: int, elite: int) -> int:
    try:
        levels = constants["maxLevel"][rarity - 1]
        return int(levels[min(elite, len(levels) - 1)])
    except Exception:
        return {0: 50, 1: 80, 2: 90}.get(elite, 90)


def module_catalog_for_operator(modules_raw, char_id: str, localized_modules_raw=None) -> Dict[str, dict]:
    result = {}

    if not isinstance(modules_raw, dict):
        return result

    equip_dict = modules_raw.get("equipDict", {})
    local_equip = (localized_modules_raw or {}).get("equipDict", {}) if isinstance(localized_modules_raw, dict) else {}
    if not isinstance(equip_dict, dict):
        return result

    for module_id, row in equip_dict.items():
        if not isinstance(row, dict):
            continue
        if row.get("charId") != char_id:
            continue
        if str(row.get("type") or "").upper() == "INITIAL":
            continue

        local_row = local_equip.get(module_id, {}) if isinstance(local_equip, dict) else {}
        result[str(module_id)] = {
            "id": str(module_id),
            "name": str(local_row.get("uniEquipName") or row.get("uniEquipName") or module_id),
            "type_1": str(row.get("typeName1") or ""),
            "type_2": str(row.get("typeName2") or ""),
            "order": int(row.get("charEquipOrder") or 999),
            "unlock_level": int(row.get("unlockLevel") or 0),
        }

    return dict(
        sorted(result.items(), key=lambda kv: (kv[1]["order"], kv[1]["name"]))
    )


def _parse_module_costs(modules_raw, char_id: str, localized_modules_raw=None):
    names: Dict[str, str] = {}
    result: Dict[str, Dict[int, CostBundle]] = {}

    if not isinstance(modules_raw, dict):
        return names, result

    equip_dict = modules_raw.get("equipDict", {})
    local_equip = (localized_modules_raw or {}).get("equipDict", {}) if isinstance(localized_modules_raw, dict) else {}
    if not isinstance(equip_dict, dict):
        return names, result

    for module_id, mod in equip_dict.items():
        if not isinstance(mod, dict) or mod.get("charId") != char_id:
            continue
        if str(mod.get("type") or "").upper() == "INITIAL":
            continue

        module_id = str(module_id)
        local_mod = local_equip.get(module_id, {}) if isinstance(local_equip, dict) else {}
        names[module_id] = str(local_mod.get("uniEquipName") or mod.get("uniEquipName") or module_id)

        item_cost = mod.get("itemCost") or {}
        per_level: Dict[int, CostBundle] = {}

        if isinstance(item_cost, dict):
            for level_key, rows in item_cost.items():
                try:
                    level = int(level_key)
                except (TypeError, ValueError):
                    continue
                if 1 <= level <= 3:
                    per_level[level] = _cost_list_to_bundle(rows)

        elif isinstance(item_cost, list):
            for idx, rows in enumerate(item_cost, start=1):
                if idx <= 3:
                    per_level[idx] = _cost_list_to_bundle(rows)

        result[module_id] = per_level

    return names, result


def build_operator_cost_model(char_id: str, characters_raw, modules_raw, localized_modules_raw=None) -> OperatorCostModel:
    row = characters_raw[char_id]
    rarity = _parse_rarity(row.get("rarity"))

    promotion_costs: Dict[int, CostBundle] = {}
    phases = row.get("phases") or []

    for elite in (1, 2):
        if elite < len(phases) and isinstance(phases[elite], dict):
            promotion_costs[elite] = _cost_list_to_bundle(
                phases[elite].get("evolveCost")
            )

    skill_rank_costs: Dict[int, CostBundle] = {}
    for idx, cond in enumerate(row.get("allSkillLvlup") or [], start=2):
        if isinstance(cond, dict):
            skill_rank_costs[idx] = _cost_list_to_bundle(
                cond.get("lvlUpCost") or cond.get("levelUpCost")
            )

    mastery_costs: Dict[str, Dict[int, CostBundle]] = {}

    for s_idx, skill in enumerate(row.get("skills") or [], start=1):
        if not isinstance(skill, dict):
            continue

        per_skill = {}

        for m_idx, cond in enumerate(skill.get("levelUpCostCond") or [], start=1):
            if m_idx > 3:
                break
            if isinstance(cond, dict):
                per_skill[m_idx] = _cost_list_to_bundle(
                    cond.get("levelUpCost") or cond.get("lvlUpCost")
                )

        mastery_costs[f"s{s_idx}"] = per_skill

    module_names, module_costs_by_id = _parse_module_costs(modules_raw, char_id, localized_modules_raw)

    return OperatorCostModel(
        operator_id=char_id,
        name=row.get("name", char_id),
        rarity=max(1, min(6, rarity)),
        promotion_costs=promotion_costs,
        skill_rank_costs=skill_rank_costs,
        mastery_costs=mastery_costs,
        module_names=module_names,
        module_costs_by_id=module_costs_by_id,
    )


def leveling_cost(
    constants: dict,
    rarity: int,
    from_elite: int,
    from_level: int,
    to_elite: int,
    to_level: int,
) -> CostBundle:
    out = CostBundle()
    exp_map = constants.get("characterExpMap") or []
    lmd_map = constants.get("characterUpgradeCostMap") or []
    evolve_gold = constants.get("evolveGoldCost") or []

    for elite in range(from_elite, to_elite + 1):
        start = from_level if elite == from_elite else 1
        end = (
            to_level
            if elite == to_elite
            else phase_max_level(constants, rarity, elite)
        )

        if elite < len(exp_map):
            arr = exp_map[elite]
            for level in range(start, end):
                if level - 1 < len(arr) and arr[level - 1] >= 0:
                    out.exp += int(arr[level - 1])

        if elite < len(lmd_map):
            arr = lmd_map[elite]
            for level in range(start, end):
                if level - 1 < len(arr) and arr[level - 1] >= 0:
                    out.lmd += int(arr[level - 1])

        if elite < to_elite:
            try:
                value = evolve_gold[rarity - 1][elite]
                if value and value > 0:
                    out.lmd += int(value)
            except Exception:
                pass

    return out
