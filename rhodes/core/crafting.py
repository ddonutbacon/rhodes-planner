from __future__ import annotations

from dataclasses import dataclass
from math import ceil
from typing import Dict, Set


@dataclass(frozen=True)
class CraftRecipe:
    output_id: str
    output_count: int
    ingredients: Dict[str, int]
    lmd_cost: int = 0


def parse_workshop_recipes(building_raw: dict) -> Dict[str, CraftRecipe]:
    if not isinstance(building_raw, dict):
        return {}

    formulas = building_raw.get("workshopFormulas") or {}

    if isinstance(formulas, dict):
        iterable = formulas.values()
    elif isinstance(formulas, list):
        iterable = formulas
    else:
        return {}

    recipes: Dict[str, CraftRecipe] = {}

    for row in iterable:
        if not isinstance(row, dict):
            continue

        output_id = str(row.get("itemId") or row.get("outputItemId") or "")
        if not output_id:
            continue

        costs = row.get("costs") or row.get("costItems") or []
        if not isinstance(costs, list) or not costs:
            continue

        ingredients: Dict[str, int] = {}

        for cost in costs:
            if not isinstance(cost, dict):
                continue

            iid = str(cost.get("id") or cost.get("itemId") or "")
            cnt = int(cost.get("count") or 0)

            if iid and cnt > 0:
                ingredients[iid] = ingredients.get(iid, 0) + cnt

        if not ingredients:
            continue

        recipes[output_id] = CraftRecipe(
            output_id=output_id,
            output_count=max(1, int(row.get("count") or row.get("outputCount") or 1)),
            ingredients=ingredients,
            lmd_cost=max(0, int(row.get("goldCost") or row.get("lmdCost") or 0)),
        )

    return recipes


def _parse_item_tier(raw) -> int:
    if raw is None:
        return 0

    if isinstance(raw, str):
        value = raw.strip().upper()

        if value.startswith("TIER_"):
            try:
                return int(value.split("_", 1)[1])
            except ValueError:
                return 0

        try:
            value = int(value)
        except ValueError:
            return 0

        return value + 1 if 0 <= value <= 4 else value

    if isinstance(raw, (int, float)):
        value = int(raw)
        return value + 1 if 0 <= value <= 4 else value

    return 0


def item_tier(item_id: str, item_meta: Dict[str, dict]) -> int:
    return _parse_item_tier(item_meta.get(item_id, {}).get("rarity"))


def recipe_depth(item_id: str, recipes: Dict[str, CraftRecipe], seen=None) -> int:
    seen = set(seen or ())

    if item_id in seen or item_id not in recipes:
        return 0

    seen.add(item_id)
    recipe = recipes[item_id]

    return 1 + max(
        (recipe_depth(iid, recipes, seen) for iid in recipe.ingredients),
        default=0,
    )


def simulate_crafting(
    required: Dict[str, float],
    owned: Dict[str, float],
    recipes: Dict[str, CraftRecipe],
    reserved_items: Set[str] | None = None,
):
    """
    Consume current stash and craft whatever is possible immediately.

    Reserved stock is treated as zero, but newly crafted copies are allowed.
    This preserves the existing pile while still letting the planner use
    workshop synthesis as part of the upgrade plan.
    """
    reserved_items = set(reserved_items or set())

    stock = {str(k): float(v or 0) for k, v in owned.items()}

    for iid in reserved_items:
        stock[iid] = 0.0

    craft_batches: Dict[str, int] = {}
    lmd_crafting = 0

    def restore(snapshot_stock, snapshot_batches, snapshot_lmd):
        nonlocal stock, craft_batches, lmd_crafting
        stock = snapshot_stock
        craft_batches = snapshot_batches
        lmd_crafting = snapshot_lmd

    def consume_or_make(item_id: str, qty: float, path: Set[str]) -> bool:
        nonlocal lmd_crafting

        if qty <= 1e-12:
            return True
        if item_id in path:
            return False

        available = stock.get(item_id, 0.0)
        take = min(available, qty)
        stock[item_id] = available - take
        qty -= take

        if qty <= 1e-12:
            return True

        recipe = recipes.get(item_id)
        if recipe is None:
            return False

        new_path = set(path)
        new_path.add(item_id)

        while qty > 1e-12:
            snapshot_stock = dict(stock)
            snapshot_batches = dict(craft_batches)
            snapshot_lmd = lmd_crafting

            ok = True
            for ing_id, ing_count in recipe.ingredients.items():
                if not consume_or_make(
                    ing_id,
                    float(ing_count),
                    new_path,
                ):
                    ok = False
                    break

            if not ok:
                restore(snapshot_stock, snapshot_batches, snapshot_lmd)
                return False

            craft_batches[item_id] = craft_batches.get(item_id, 0) + 1
            lmd_crafting += recipe.lmd_cost

            produced = float(recipe.output_count)
            used = min(produced, qty)
            qty -= used

            excess = produced - used
            if excess > 0:
                stock[item_id] = stock.get(item_id, 0.0) + excess

        return True

    item_rows = []
    remaining: Dict[str, float] = {}

    ordered = sorted(
        required.items(),
        key=lambda kv: (-recipe_depth(kv[0], recipes), kv[0]),
    )

    for item_id, raw_qty in ordered:
        needed = float(raw_qty or 0)
        if needed <= 0:
            continue

        before_stock = stock.get(item_id, 0.0)
        direct = min(before_stock, needed)
        stock[item_id] = before_stock - direct
        left = needed - direct
        crafted_used = 0.0

        while left > 1e-12 and item_id in recipes:
            recipe = recipes[item_id]

            snapshot_stock = dict(stock)
            snapshot_batches = dict(craft_batches)
            snapshot_lmd = lmd_crafting

            ok = True
            for ing_id, ing_count in recipe.ingredients.items():
                if not consume_or_make(
                    ing_id,
                    float(ing_count),
                    {item_id},
                ):
                    ok = False
                    break

            if not ok:
                restore(snapshot_stock, snapshot_batches, snapshot_lmd)
                break

            craft_batches[item_id] = craft_batches.get(item_id, 0) + 1
            lmd_crafting += recipe.lmd_cost

            produced = float(recipe.output_count)
            used = min(produced, left)
            crafted_used += used
            left -= used

            excess = produced - used
            if excess > 0:
                stock[item_id] = stock.get(item_id, 0.0) + excess

        if left > 1e-12:
            remaining[item_id] = left

        item_rows.append({
            "item_id": item_id,
            "required": needed,
            "from_stash": direct,
            "crafted": crafted_used,
            "remaining": max(0.0, left),
            "reserved": item_id in reserved_items,
        })

    craft_ops = []

    for output_id, batches in sorted(craft_batches.items()):
        recipe = recipes[output_id]

        craft_ops.append({
            "output_id": output_id,
            "batches": batches,
            "output_quantity": batches * recipe.output_count,
            "ingredients": {
                iid: cnt * batches
                for iid, cnt in recipe.ingredients.items()
            },
            "lmd_cost": recipe.lmd_cost * batches,
        })

    return {
        "item_rows": item_rows,
        "craft_ops": craft_ops,
        "remaining": remaining,
        "lmd_crafting": int(lmd_crafting),
        "stock_after": stock,
    }


def expand_high_tier_farm_targets(
    remaining: Dict[str, float],
    stock_after: Dict[str, float],
    recipes: Dict[str, CraftRecipe],
    item_meta: Dict[str, dict],
    stop_tier: int = 3,
):
    """
    Expand remaining T4/T5 materials into workshop ingredients until T3.

    Result:
      - farm_targets: materials the stage solver should actually farm
      - future_craft_ops: synthesis to perform after those inputs are farmed
      - lmd_crafting: LMD needed for those future workshop crafts

    This intentionally prefers farming T3 inputs over direct T4 drops.
    """
    stock = {str(k): float(v or 0) for k, v in stock_after.items()}
    farm_targets: Dict[str, float] = {}
    future_batches: Dict[str, int] = {}
    future_lmd = 0

    def add_farm(iid: str, qty: float):
        if qty > 1e-12:
            farm_targets[iid] = farm_targets.get(iid, 0.0) + qty

    def satisfy_future(iid: str, qty: float, path: Set[str]):
        nonlocal future_lmd

        if qty <= 1e-12:
            return

        available = stock.get(iid, 0.0)
        take = min(available, qty)
        stock[iid] = available - take
        qty -= take

        if qty <= 1e-12:
            return

        tier = item_tier(iid, item_meta)
        recipe = recipes.get(iid)

        if recipe is None or tier <= stop_tier or iid in path:
            add_farm(iid, qty)
            return

        batches = int(ceil(qty / recipe.output_count))
        future_batches[iid] = future_batches.get(iid, 0) + batches
        future_lmd += recipe.lmd_cost * batches

        new_path = set(path)
        new_path.add(iid)

        for ingredient_id, ingredient_count in recipe.ingredients.items():
            satisfy_future(
                ingredient_id,
                float(ingredient_count * batches),
                new_path,
            )

        produced = batches * recipe.output_count
        excess = produced - qty
        if excess > 1e-12:
            stock[iid] = stock.get(iid, 0.0) + excess

    ordered = sorted(
        remaining.items(),
        key=lambda kv: (-item_tier(kv[0], item_meta), kv[0]),
    )

    for iid, qty in ordered:
        satisfy_future(iid, float(qty), set())

    future_ops = []

    for output_id, batches in sorted(future_batches.items()):
        recipe = recipes[output_id]

        future_ops.append({
            "output_id": output_id,
            "batches": batches,
            "output_quantity": batches * recipe.output_count,
            "ingredients": {
                iid: count * batches
                for iid, count in recipe.ingredients.items()
            },
            "lmd_cost": recipe.lmd_cost * batches,
        })

    return {
        "farm_targets": farm_targets,
        "future_craft_ops": future_ops,
        "lmd_crafting": int(future_lmd),
        "stock_after": stock,
    }


def expand_reserved_requirements(
    required: Dict[str, float],
    recipes: Dict[str, CraftRecipe],
    item_meta: Dict[str, dict],
    stop_tier: int = 3,
):
    """
    Expand reserved requirements without consuming *any* owned ingredients.

    This implements the user's explicit reserve policy:
      - the reserved top-level item is not taken from depot;
      - for craftable T4/T5 items, every ingredient needed to create the
        reserved quantity is also planned as newly obtained rather than taken
        from depot;
      - expansion stops at T3, which becomes the farming target.

    Non-craftable items and items at/below ``stop_tier`` are farmed directly.
    """
    farm_targets: Dict[str, float] = {}
    future_batches: Dict[str, int] = {}
    future_lmd = 0

    def add_farm(iid: str, qty: float):
        if qty > 1e-12:
            farm_targets[iid] = farm_targets.get(iid, 0.0) + qty

    def expand(iid: str, qty: float, path: Set[str]):
        nonlocal future_lmd

        if qty <= 1e-12:
            return

        recipe = recipes.get(iid)
        tier = item_tier(iid, item_meta)

        if recipe is None or tier <= stop_tier or iid in path:
            add_farm(iid, qty)
            return

        batches = int(ceil(qty / recipe.output_count))
        future_batches[iid] = future_batches.get(iid, 0) + batches
        future_lmd += recipe.lmd_cost * batches

        next_path = set(path)
        next_path.add(iid)

        for ingredient_id, ingredient_count in recipe.ingredients.items():
            expand(
                ingredient_id,
                float(ingredient_count * batches),
                next_path,
            )

    for iid, qty in sorted(required.items()):
        expand(str(iid), float(qty or 0), set())

    future_ops = []

    for output_id, batches in sorted(future_batches.items()):
        recipe = recipes[output_id]
        future_ops.append({
            "output_id": output_id,
            "batches": batches,
            "output_quantity": batches * recipe.output_count,
            "ingredients": {
                iid: count * batches
                for iid, count in recipe.ingredients.items()
            },
            "lmd_cost": recipe.lmd_cost * batches,
            "source": "reserved",
        })

    return {
        "farm_targets": farm_targets,
        "future_craft_ops": future_ops,
        "lmd_crafting": int(future_lmd),
    }


def merge_farm_expansions(*expansions):
    """Merge multiple farm/crafting expansion results into one view."""
    farm_targets: Dict[str, float] = {}
    future_ops = []
    lmd_crafting = 0

    for expansion in expansions:
        if not expansion:
            continue

        for iid, qty in expansion.get("farm_targets", {}).items():
            farm_targets[iid] = farm_targets.get(iid, 0.0) + float(qty or 0)

        future_ops.extend(expansion.get("future_craft_ops", []))
        lmd_crafting += int(expansion.get("lmd_crafting", 0) or 0)

    return {
        "farm_targets": farm_targets,
        "future_craft_ops": future_ops,
        "lmd_crafting": lmd_crafting,
    }
