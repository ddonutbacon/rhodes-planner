from __future__ import annotations

import json
import math

from rhodes.core.models import Inventory

EXP_CARD_VALUES = {
    "2001": 200,
    "2002": 400,
    "2003": 1000,
    "2004": 2000,
}


def exp_points_to_card_needs(exp_points: int) -> dict[str, int]:
    """Convert EXP points into a deterministic T4-first Battle Record mix."""
    remaining = max(0, int(exp_points or 0))
    needs = {iid: 0 for iid in EXP_CARD_VALUES}

    for iid in ("2004", "2003", "2002", "2001"):
        value = EXP_CARD_VALUES[iid]
        count, remaining = divmod(remaining, value)
        needs[iid] = count

    # Never under-provision a non-zero remainder below one T1 record.
    if remaining > 0:
        needs["2001"] += 1

    return needs


def build_penguin_planner_config_payload(
    *,
    inventory: Inventory,
    farm_targets: dict[str, float],
    additional_lmd: int,
    additional_exp: int,
    item_meta: dict,
):
    """
    Build a Penguin Statistics browser Planner config for the *effective farm
    problem* Rhodes Planner has already calculated.

    Penguin's browser config stores absolute ``need`` and current ``have``.
    Rhodes' farming engine stores the incremental amount that still has to be
    obtained after stash use, reserve policy, crafting expansion and passive
    base production.

    Therefore, for every farming target:

        Penguin need = current have + Rhodes incremental farm target

    This is intentional. If a user reserves a T4/T5 item, Rhodes expands that
    requirement into lower-tier farm targets while ignoring the relevant owned
    ingredient chain. Exporting the original high-tier requirement would let
    Penguin subtract the user's stash again and incorrectly conclude that no
    farming is necessary.
    """
    have: dict[str, int] = {
        str(iid): max(0, int(math.floor(float(qty or 0))))
        for iid, qty in inventory.materials.items()
    }

    # ArkPRTS stores LMD separately from normal inventory.
    have["4001"] = max(0, int(inventory.lmd or 0))

    for iid, count in inventory.exp_cards.items():
        have[str(iid)] = max(0, int(count or 0))

    # Penguin's `need` is an absolute target, not an incremental deficit.
    need: dict[str, int] = {}

    for iid, qty in farm_targets.items():
        iid = str(iid)
        increment = max(0, int(math.ceil(float(qty or 0))))
        if increment > 0:
            need[iid] = have.get(iid, 0) + increment

    lmd_increment = max(0, int(additional_lmd or 0))
    if lmd_increment > 0:
        need["4001"] = have.get("4001", 0) + lmd_increment

    exp_increments = exp_points_to_card_needs(additional_exp)
    for iid, increment in exp_increments.items():
        if increment > 0:
            need[iid] = have.get(iid, 0) + int(increment)

    # Keep existing depot rows as `need: 0` where they are not part of the
    # effective farm problem. This mirrors Penguin's own exported config shape.
    all_ids = set(have) | set(need) | set(EXP_CARD_VALUES) | {"4001"}

    def sort_key(iid: str):
        name = str(item_meta.get(iid, {}).get("name") or iid)
        return (name.lower(), iid)

    items = [
        {
            "id": iid,
            "need": int(need.get(iid, 0)),
            "have": int(have.get(iid, 0)),
        }
        for iid in sorted(all_ids, key=sort_key)
    ]

    return {
        "@type": "@penguin-statistics/planner/config",
        "items": items,
    }


def build_penguin_planner_config_json(**kwargs) -> str:
    return json.dumps(
        build_penguin_planner_config_payload(**kwargs),
        ensure_ascii=False,
        separators=(",", ":"),
    )
