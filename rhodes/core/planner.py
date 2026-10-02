from __future__ import annotations
from typing import Iterable, Set

from .models import (
    CostBundle,
    Inventory,
    OperatorState,
    UpgradeGoal,
    OperatorCostModel,
)


def calculate_upgrade_cost(
    current: OperatorState,
    target: UpgradeGoal,
    model: OperatorCostModel,
    constants: dict,
    leveling_fn,
) -> CostBundle:
    if current.operator_id != target.operator_id:
        raise ValueError("Current and target operator IDs do not match.")

    if target.elite < current.elite:
        raise ValueError("Target Elite rank cannot be below the current account state.")

    if target.elite == current.elite and target.level < current.level:
        raise ValueError("Target level cannot be below the current account state.")

    if target.skill_level < current.skill_level:
        raise ValueError("Target skill rank cannot be below the current account state.")

    out = leveling_fn(
        constants,
        model.rarity,
        current.elite,
        current.level,
        target.elite,
        target.level,
    )

    for elite in range(current.elite + 1, target.elite + 1):
        b = model.promotion_costs.get(elite)
        if b:
            for k, v in b.materials.items():
                out.materials[k] = out.materials.get(k, 0) + v

    for rank in range(current.skill_level + 1, target.skill_level + 1):
        b = model.skill_rank_costs.get(rank)
        if b:
            out.add(b)

    for skill in ("s1", "s2", "s3"):
        current_level = getattr(current.mastery, skill)
        target_level = getattr(target.mastery, skill)

        if target_level < current_level:
            raise ValueError(
                f"{skill.upper()} mastery target cannot be below the current account state."
            )

        for m in range(current_level + 1, target_level + 1):
            b = model.mastery_costs.get(skill, {}).get(m)
            if b:
                out.add(b)

    if target.module_id:
        current_module_level = 0
        if target.module_id in current.modules:
            current_module_level = current.modules[target.module_id].level

        if target.module_level < current_module_level:
            raise ValueError(
                "Target module level cannot be below the current account state."
            )

        per_level = model.module_costs_by_id.get(target.module_id, {})

        for level in range(current_module_level + 1, target.module_level + 1):
            b = per_level.get(level)
            if b:
                out.add(b)

    elif target.module_level:
        raise ValueError("A module must be selected before setting a module target.")

    return out


def aggregate_costs(costs: Iterable[CostBundle]) -> CostBundle:
    out = CostBundle()
    for c in costs:
        out.add(c)
    return out


def calculate_deficit(
    required: CostBundle,
    owned: Inventory,
    *,
    reserved_materials: Set[str] | None = None,
    farm_full_lmd: bool = False,
    farm_full_exp: bool = False,
) -> CostBundle:
    """
    Deficit before crafting.

    A reserved resource is deliberately ignored from owned stash so that the
    user can preserve their stockpile and farm the full requirement instead.
    """
    reserved_materials = set(reserved_materials or set())

    out = CostBundle(
        lmd=required.lmd if farm_full_lmd else max(0, required.lmd - owned.lmd),
        exp=required.exp if farm_full_exp else max(0, required.exp - owned.exp),
    )

    for iid, qty in required.materials.items():
        owned_qty = 0 if iid in reserved_materials else owned.materials.get(iid, 0)
        remain = max(0.0, float(qty) - float(owned_qty))
        if remain > 1e-12:
            out.materials[iid] = remain

    return out
