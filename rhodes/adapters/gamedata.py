from __future__ import annotations
from typing import Any, Dict

from .http import get_json
from rhodes.core.models import CostBundle, OperatorCostModel

BASE = "https://raw.githubusercontent.com/ArknightsAssets/ArknightsGamedata/master/en/gamedata/excel"

URLS = {
    "characters": f"{BASE}/character_table.json",
    "items": f"{BASE}/item_table.json",
    "constants": f"{BASE}/gamedata_const.json",
    "modules": f"{BASE}/uniequip_table.json",
    "stages": f"{BASE}/stage_table.json",
    "building": f"{BASE}/building_data.json",
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

    return filtered


def fetch_game_data():
    characters = get_json(URLS["characters"], "character_table", 24)
    items = get_json(URLS["items"], "item_table", 24)
    constants = get_json(URLS["constants"], "gamedata_const", 24)
    modules = get_json(URLS["modules"], "uniequip_table", 24)
    stages = get_json(URLS["stages"], "stage_table", 24)

    # Crafting is optional: failure here must not disable the main planner.
    try:
        building = get_json(URLS["building"], "building_data", 24)
    except Exception:
        building = {}

    return characters, items, constants, modules, stages, building


def build_item_metadata_map(items_raw) -> Dict[str, dict]:
    items = _unwrap_items(items_raw)
    out = {}

    for iid, row in items.items():
        if not isinstance(row, dict):
            continue

        out[str(iid)] = {
            "id": str(iid),
            "name": str(row.get("name") or iid),
            "icon_id": str(row.get("iconId") or iid),
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


def operator_catalog(characters_raw) -> Dict[str, dict]:
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

        out[cid] = {
            "id": cid,
            "name": name,
            "rarity": max(1, min(6, rarity)),
            "profession": profession,
            "class": profession_label(profession),
        }

    return out


def phase_max_level(constants: dict, rarity: int, elite: int) -> int:
    try:
        levels = constants["maxLevel"][rarity - 1]
        return int(levels[min(elite, len(levels) - 1)])
    except Exception:
        return {0: 50, 1: 80, 2: 90}.get(elite, 90)


def module_catalog_for_operator(modules_raw, char_id: str) -> Dict[str, dict]:
    result = {}

    if not isinstance(modules_raw, dict):
        return result

    equip_dict = modules_raw.get("equipDict", {})
    if not isinstance(equip_dict, dict):
        return result

    for module_id, row in equip_dict.items():
        if not isinstance(row, dict):
            continue
        if row.get("charId") != char_id:
            continue
        if str(row.get("type") or "").upper() == "INITIAL":
            continue

        result[str(module_id)] = {
            "id": str(module_id),
            "name": str(row.get("uniEquipName") or module_id),
            "type_1": str(row.get("typeName1") or ""),
            "type_2": str(row.get("typeName2") or ""),
            "order": int(row.get("charEquipOrder") or 999),
            "unlock_level": int(row.get("unlockLevel") or 0),
        }

    return dict(
        sorted(result.items(), key=lambda kv: (kv[1]["order"], kv[1]["name"]))
    )


def _parse_module_costs(modules_raw, char_id: str):
    names: Dict[str, str] = {}
    result: Dict[str, Dict[int, CostBundle]] = {}

    if not isinstance(modules_raw, dict):
        return names, result

    equip_dict = modules_raw.get("equipDict", {})
    if not isinstance(equip_dict, dict):
        return names, result

    for module_id, mod in equip_dict.items():
        if not isinstance(mod, dict) or mod.get("charId") != char_id:
            continue
        if str(mod.get("type") or "").upper() == "INITIAL":
            continue

        module_id = str(module_id)
        names[module_id] = str(mod.get("uniEquipName") or module_id)

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


def build_operator_cost_model(char_id: str, characters_raw, modules_raw) -> OperatorCostModel:
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

    module_names, module_costs_by_id = _parse_module_costs(modules_raw, char_id)

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
