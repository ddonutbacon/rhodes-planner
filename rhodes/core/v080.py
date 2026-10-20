from __future__ import annotations

import json
from copy import deepcopy
from typing import Any

from rhodes.core.models import Inventory, OperatorState


def stable_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), default=str)


def normalised_snapshot(inventory: Inventory, operators: dict[str, OperatorState], metadata: dict | None = None) -> dict:
    return {
        "inventory": inventory.model_dump(),
        "operators": {str(cid): op.model_dump() for cid, op in operators.items()},
        "metadata": dict(metadata or {}),
    }


def diff_import(current_inventory: Inventory, current_operators: dict[str, OperatorState],
                new_inventory: Inventory, new_operators: dict[str, OperatorState]) -> dict:
    changed_ops = 0
    added_ops = 0
    removed_ops = 0
    current_ids = set(current_operators)
    new_ids = set(new_operators)
    for cid in current_ids & new_ids:
        if current_operators[cid].model_dump() != new_operators[cid].model_dump():
            changed_ops += 1
    added_ops = len(new_ids - current_ids)
    removed_ops = len(current_ids - new_ids)

    material_ids = set(current_inventory.materials) | set(new_inventory.materials)
    changed_materials = sum(
        1 for iid in material_ids
        if float(current_inventory.materials.get(iid, 0) or 0)
        != float(new_inventory.materials.get(iid, 0) or 0)
    )
    return {
        "lmd_before": int(current_inventory.lmd),
        "lmd_after": int(new_inventory.lmd),
        "exp_before": int(current_inventory.exp),
        "exp_after": int(new_inventory.exp),
        "changed_operators": changed_ops,
        "added_operators": added_ops,
        "removed_operators": removed_ops,
        "changed_materials": changed_materials,
    }


def _operator_manually_changed(cid: str, editable: dict[str, OperatorState], previous_snapshot: dict) -> bool:
    previous = (previous_snapshot.get("operators") or {}).get(cid)
    current = editable.get(cid)
    if current is None:
        return previous is not None
    if previous is None:
        return True
    return current.model_dump() != previous


def merge_import_preserving_manual(
    *,
    current_inventory: Inventory,
    current_operators: dict[str, OperatorState],
    previous_snapshot: dict | None,
    imported_inventory: Inventory,
    imported_operators: dict[str, OperatorState],
) -> tuple[Inventory, dict[str, OperatorState], dict]:
    """
    Merge a fresh import while keeping values that the user manually changed
    since the previous import snapshot.

    Operator preservation is intentionally coarse: if any saved operator state
    differs from the previous snapshot, that operator is kept whole.
    Inventory preservation is quantity-by-quantity.
    """
    previous_snapshot = previous_snapshot or {}
    previous_inv = previous_snapshot.get("inventory") or {}
    previous_mats = previous_inv.get("materials") or {}
    previous_cards = previous_inv.get("exp_cards") or {}

    merged_inv = imported_inventory.model_copy(deep=True)
    preserved_resources = 0

    # Preserve manually edited LMD / EXP-card quantities by comparing current
    # editable values with the prior imported snapshot.
    prev_lmd = int(previous_inv.get("lmd", current_inventory.lmd) or 0)
    if int(current_inventory.lmd) != prev_lmd:
        merged_inv.lmd = int(current_inventory.lmd)
        preserved_resources += 1

    all_mat_ids = set(imported_inventory.materials) | set(current_inventory.materials) | set(previous_mats)
    for iid in all_mat_ids:
        old = float(previous_mats.get(iid, 0) or 0)
        cur = float(current_inventory.materials.get(iid, 0) or 0)
        if cur != old:
            merged_inv.materials[str(iid)] = cur
            preserved_resources += 1

    all_card_ids = set(imported_inventory.exp_cards) | set(current_inventory.exp_cards) | set(previous_cards)
    for iid in all_card_ids:
        old = int(previous_cards.get(iid, 0) or 0)
        cur = int(current_inventory.exp_cards.get(iid, 0) or 0)
        if cur != old:
            merged_inv.exp_cards[str(iid)] = cur

    # EXP is derived by the app after merge from card counts.
    merged_ops = {cid: op.model_copy(deep=True) for cid, op in imported_operators.items()}
    preserved_ops = 0
    for cid, op in current_operators.items():
        if _operator_manually_changed(cid, current_operators, previous_snapshot):
            merged_ops[cid] = op.model_copy(deep=True)
            preserved_ops += 1

    return merged_inv, merged_ops, {
        "preserved_operator_overrides": preserved_ops,
        "preserved_resource_overrides": preserved_resources,
    }


def spendable_inventory(
    inventory: Inventory,
    *,
    reserved_materials: dict[str, float] | None = None,
    reserved_lmd: int = 0,
    reserved_exp: int = 0,
) -> Inventory:
    out = inventory.model_copy(deep=True)
    out.lmd = max(0, int(out.lmd) - max(0, int(reserved_lmd)))
    out.exp = max(0, int(out.exp) - max(0, int(reserved_exp)))

    for iid, reserved in (reserved_materials or {}).items():
        owned = float(out.materials.get(str(iid), 0) or 0)
        out.materials[str(iid)] = max(0.0, owned - max(0.0, float(reserved or 0)))
    return out


def active_goal_pairs(goals: list[dict], costs: list[dict]) -> list[tuple[dict, dict]]:
    return [
        (goal, cost)
        for goal, cost in zip(goals, costs)
        if bool(goal.get("active", True))
    ]


def move_list_item(values: list, index: int, direction: int) -> list:
    out = list(values)
    new_index = index + direction
    if not (0 <= index < len(out)) or not (0 <= new_index < len(out)):
        return out
    out[index], out[new_index] = out[new_index], out[index]
    return out


def plan_signature(*, goals: list[dict], costs: list[dict], inventory: Inventory,
                   reserves: dict[str, float], reserve_lmd: int, reserve_exp: int,
                   planning_days: float, base_lmd_per_day: int, base_t3_per_day: int) -> str:
    payload = {
        "goals": goals,
        "costs": costs,
        "inventory": inventory.model_dump(),
        "reserves": reserves,
        "reserve_lmd": reserve_lmd,
        "reserve_exp": reserve_exp,
        "planning_days": planning_days,
        "base_lmd_per_day": base_lmd_per_day,
        "base_t3_per_day": base_t3_per_day,
    }
    return stable_json(payload)


CHIP_CATALYST_ID = "32001"
PURCHASE_CERTIFICATE_ID = "4006"
CHIP_CATALYST_CERT_COST = 90


def resolve_special_acquisitions(
    farm_targets: dict[str, float],
    spendable_inventory: Inventory,
) -> tuple[dict[str, float], list[dict]]:
    """
    Convert non-stage upgrade resources into their actual farmable acquisition
    currency where Rhodes knows a stable route.

    Chip Catalyst is bought from the Purchase Certificate store for 90
    Purchase Certificates each. Purchase Certificates themselves are farmed
    from AP stages (normally AP-5).
    """
    targets = {
        str(iid): float(qty or 0)
        for iid, qty in (farm_targets or {}).items()
        if float(qty or 0) > 1e-12
    }
    notes: list[dict] = []

    catalyst_missing = int(__import__("math").ceil(targets.pop(CHIP_CATALYST_ID, 0.0)))
    if catalyst_missing > 0:
        certificates_required = catalyst_missing * CHIP_CATALYST_CERT_COST
        certificates_owned = int(
            max(
                0,
                float(
                    spendable_inventory.materials.get(
                        PURCHASE_CERTIFICATE_ID,
                        0,
                    )
                    or 0
                ),
            )
        )
        certificates_to_farm = max(0, certificates_required - certificates_owned)

        if certificates_to_farm > 0:
            targets[PURCHASE_CERTIFICATE_ID] = (
                targets.get(PURCHASE_CERTIFICATE_ID, 0.0)
                + certificates_to_farm
            )

        notes.append({
            "source_item_id": CHIP_CATALYST_ID,
            "farm_item_id": PURCHASE_CERTIFICATE_ID,
            "source_quantity": catalyst_missing,
            "currency_required": certificates_required,
            "currency_owned": certificates_owned,
            "currency_to_farm": certificates_to_farm,
            "summary": (
                f"Chip Catalyst ×{catalyst_missing}: buy from the Purchase Certificate "
                f"store at {CHIP_CATALYST_CERT_COST} Purchase Certificates each "
                f"({certificates_required:,} required"
                + (
                    f"; {certificates_owned:,} spendable already owned; "
                    f"{certificates_to_farm:,} still to farm)."
                    if certificates_owned > 0
                    else f"; {certificates_to_farm:,} to farm)."
                )
            ),
        })

    return targets, notes
