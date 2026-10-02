from rhodes.core.crafting import (
    CraftRecipe,
    expand_high_tier_farm_targets,
    simulate_crafting,
)
from rhodes.core.farming import build_farming_plan
from rhodes.core.models import CostBundle, StageModel


def test_reserved_owned_copy_is_protected_but_new_copy_can_be_crafted():
    recipes = {
        "t4": CraftRecipe(
            output_id="t4",
            output_count=1,
            ingredients={"t3": 2},
        )
    }

    result = simulate_crafting(
        required={"t4": 1},
        owned={"t4": 9, "t3": 2},
        recipes=recipes,
        reserved_items={"t4"},
    )

    row = result["item_rows"][0]
    assert row["from_stash"] == 0
    assert row["crafted"] == 1
    assert result["remaining"] == {}


def test_t4_missing_expands_to_t3_farm_target():
    recipes = {
        "t4": CraftRecipe(
            output_id="t4",
            output_count=1,
            ingredients={"t3": 2},
            lmd_cost=100,
        )
    }

    item_meta = {
        "t4": {"rarity": "TIER_4"},
        "t3": {"rarity": "TIER_3"},
    }

    result = expand_high_tier_farm_targets(
        remaining={"t4": 3},
        stock_after={"t3": 1},
        recipes=recipes,
        item_meta=item_meta,
        stop_tier=3,
    )

    assert "t4" not in result["farm_targets"]
    assert result["farm_targets"]["t3"] == 5
    assert result["lmd_crafting"] == 300


def test_lmd_prefers_ce6_and_exp_prefers_ls6():
    stages = [
        StageModel(
            stage_id="other_lmd",
            code="1-1",
            sanity_cost=6,
            lmd_per_run=1000,
        ),
        StageModel(
            stage_id="ce6",
            code="CE-6",
            sanity_cost=36,
            lmd_per_run=10000,
        ),
        StageModel(
            stage_id="ls6",
            code="LS-6",
            sanity_cost=36,
            exp_per_run=10000,
        ),
    ]

    plan = build_farming_plan(
        CostBundle(lmd=20001, exp=10001),
        stages,
    )

    lmd = next(x for x in plan.lines if x.purpose == "LMD")
    exp = next(x for x in plan.lines if x.purpose == "EXP")

    assert lmd.stage_code == "CE-6"
    assert lmd.runs == 3
    assert exp.stage_code == "LS-6"
    assert exp.runs == 2


def test_reserved_t5_ignores_owned_component_chain_and_farms_t3():
    from rhodes.core.crafting import expand_reserved_requirements

    recipes = {
        "t5": CraftRecipe(
            output_id="t5",
            output_count=1,
            ingredients={"t4": 2},
            lmd_cost=200,
        ),
        "t4": CraftRecipe(
            output_id="t4",
            output_count=1,
            ingredients={"t3": 3},
            lmd_cost=100,
        ),
    }

    item_meta = {
        "t5": {"rarity": "TIER_5"},
        "t4": {"rarity": "TIER_4"},
        "t3": {"rarity": "TIER_3"},
    }

    result = expand_reserved_requirements(
        required={"t5": 2},
        recipes=recipes,
        item_meta=item_meta,
        stop_tier=3,
    )

    # Two T5 need four T4; four T4 need twelve T3. Existing depot is
    # intentionally irrelevant for a reserved requirement chain.
    assert result["farm_targets"] == {"t3": 12}
    assert result["lmd_crafting"] == 800


def test_reserved_t3_is_farmed_directly():
    from rhodes.core.crafting import expand_reserved_requirements

    result = expand_reserved_requirements(
        required={"t3": 7},
        recipes={},
        item_meta={"t3": {"rarity": "TIER_3"}},
        stop_tier=3,
    )

    assert result["farm_targets"] == {"t3": 7}
