from __future__ import annotations

from typing import Any, Dict, Tuple

from rhodes.core.models import (
    Inventory,
    ModuleProgress,
    OperatorState,
    SkillState,
)

# Canonical battle-record item IDs and EXP values.
# These are account inventory items, not operator EXP values.
EXP_CARD_VALUES = {
    "2001": 200,   # Drill Battle Record
    "2002": 400,   # Frontline Battle Record
    "2003": 1000,  # Tactical Battle Record
    "2004": 2000,  # Strategic Battle Record
}


def _skills_to_mastery(skills: Any) -> SkillState:
    values = []
    if isinstance(skills, list):
        for row in skills[:3]:
            if isinstance(row, dict):
                values.append(int(row.get("specializeLevel", 0) or 0))
            else:
                values.append(0)

    while len(values) < 3:
        values.append(0)

    return SkillState(s1=values[0], s2=values[1], s3=values[2])


def _modules(equip: Any) -> Dict[str, ModuleProgress]:
    out: Dict[str, ModuleProgress] = {}

    if not isinstance(equip, dict):
        return out

    for module_id, row in equip.items():
        if not isinstance(row, dict):
            continue

        out[str(module_id)] = ModuleProgress(
            level=int(row.get("level", 0) or 0),
            locked=bool(row.get("locked", 0)),
            hidden=bool(row.get("hide", 0)),
        )

    return out


def _parse_forms(tmpl: Any) -> Dict[str, dict]:
    """
    Preserve alternate-form state (notably Amiya) without forcing it into
    the generic one-form operator model.

    This lets the planner add form-specific skill/module handling later
    without losing information during import.
    """
    out: Dict[str, dict] = {}

    if not isinstance(tmpl, dict):
        return out

    for form_id, row in tmpl.items():
        if not isinstance(row, dict):
            continue

        out[str(form_id)] = {
            "skin_id": row.get("skinId"),
            "default_skill_index": row.get("defaultSkillIndex"),
            "mastery": _skills_to_mastery(row.get("skills")).model_dump(),
            "current_module_id": row.get("currentEquip"),
            "modules": {
                k: v.model_dump()
                for k, v in _modules(row.get("equip")).items()
            },
        }

    return out


def parse_arkprts_full_export(payload: Dict[str, Any]) -> Tuple[Inventory, Dict[str, OperatorState], dict]:
    """
    Parse ArkPRTS / arkprtserver private raw-user syncData export.

    Privacy design:
    - UID, nickname, auth tokens and friend data are NOT copied into the
      normalized account model.
    - Only planner-relevant account state is retained.
    """
    if not isinstance(payload, dict):
        raise ValueError("ARKprts export must be a JSON object.")

    status = payload.get("status")
    inventory_raw = payload.get("inventory")
    troop = payload.get("troop")

    if not isinstance(status, dict):
        raise ValueError("Missing ARKprts status object.")
    if not isinstance(inventory_raw, dict):
        raise ValueError("Missing ARKprts inventory object.")
    if not isinstance(troop, dict) or not isinstance(troop.get("chars"), dict):
        raise ValueError("Missing ARKprts troop.chars object.")

    materials = {}
    exp_cards = {}

    for item_id, raw_count in inventory_raw.items():
        try:
            count = int(raw_count or 0)
        except (TypeError, ValueError):
            continue

        item_id = str(item_id)
        materials[item_id] = count

        if item_id in EXP_CARD_VALUES:
            exp_cards[item_id] = count

    exp_points = sum(
        exp_cards.get(item_id, 0) * value
        for item_id, value in EXP_CARD_VALUES.items()
    )

    inv = Inventory(
        lmd=int(status.get("gold", 0) or 0),
        exp=exp_points,
        exp_cards=exp_cards,
        orundum=int(status.get("diamondShard", 0) or 0),
        originite_prime=int(status.get("freeDiamond", 0) or 0)
        + int(status.get("payDiamond", 0) or 0),
        materials=materials,
    )

    operators: Dict[str, OperatorState] = {}

    for _, row in troop["chars"].items():
        if not isinstance(row, dict):
            continue

        char_id = str(row.get("charId") or "")
        if not char_id:
            continue

        forms = _parse_forms(row.get("tmpl"))
        active_form_id = row.get("currentTmpl")

        skills = row.get("skills") or []
        equip = row.get("equip") or {}
        current_equip = row.get("currentEquip")

        # Amiya and other template-based operators can store active-form
        # skill/module state inside tmpl rather than the top-level char row.
        if active_form_id and active_form_id in forms:
            active = forms[active_form_id]
            if not skills:
                mastery_dict = active.get("mastery", {})
                mastery = SkillState.model_validate(mastery_dict)
            else:
                mastery = _skills_to_mastery(skills)

            if not equip:
                modules = {
                    k: ModuleProgress.model_validate(v)
                    for k, v in active.get("modules", {}).items()
                }
            else:
                modules = _modules(equip)

            if current_equip is None:
                current_equip = active.get("current_module_id")
        else:
            mastery = _skills_to_mastery(skills)
            modules = _modules(equip)

        active_module_level = 0
        if current_equip and current_equip in modules:
            active_module_level = modules[current_equip].level

        operators[char_id] = OperatorState(
            operator_id=char_id,
            name=char_id,  # resolved to localized name using static game data in UI
            elite=int(row.get("evolvePhase", 0) or 0),
            level=max(1, int(row.get("level", 1) or 1)),
            skill_level=max(1, int(row.get("mainSkillLvl", 1) or 1)),
            mastery=mastery,
            module_level=max(0, min(3, active_module_level)),
            current_module_id=current_equip,
            modules=modules,
            potential_rank=int(row.get("potentialRank", 0) or 0),
            forms=forms,
        )

    # Account-neutral diagnostics only. Do not surface UID or nickname.
    e2_count = sum(1 for op in operators.values() if op.elite == 2)
    m3_count = sum(
        int(op.mastery.s1 == 3)
        + int(op.mastery.s2 == 3)
        + int(op.mastery.s3 == 3)
        for op in operators.values()
    )
    module_record_count = sum(len(op.modules) for op in operators.values())

    dungeon = payload.get("dungeon", {})
    stage_records = 0
    if isinstance(dungeon, dict) and isinstance(dungeon.get("stages"), dict):
        stage_records = len(dungeon["stages"])

    metadata = {
        "source": "ARKprts full data export",
        "account_level": int(status.get("level", 0) or 0),
        "server_name": status.get("serverName"),
        "operator_count": len(operators),
        "e2_operator_count": e2_count,
        "m3_skill_count": m3_count,
        "inventory_entry_count": len(materials),
        "positive_inventory_entry_count": sum(1 for x in materials.values() if x > 0),
        "module_record_count": module_record_count,
        "stage_record_count": stage_records,
        "special_progression_record_count": len(troop.get("spOperator", {}) or {}),
    }

    return inv, operators, metadata
