from rhodes.core.crafting import CraftRecipe, simulate_crafting
from rhodes.core.models import (
    CostBundle,
    Inventory,
    ModuleProgress,
    OperatorCostModel,
    OperatorState,
    SkillState,
    UpgradeGoal,
)
from rhodes.core.planner import calculate_deficit, calculate_upgrade_cost


def fake_leveling(*args, **kwargs):
    return CostBundle()


def test_reserve_stash_farms_full_requirement():
    required = CostBundle(
        lmd=1000,
        exp=500,
        materials={"rock": 10},
    )
    owned = Inventory(
        lmd=900,
        exp=500,
        materials={"rock": 9},
    )

    deficit = calculate_deficit(
        required,
        owned,
        reserved_materials={"rock"},
        farm_full_lmd=True,
        farm_full_exp=True,
    )

    assert deficit.lmd == 1000
    assert deficit.exp == 500
    assert deficit.materials["rock"] == 10


def test_recursive_crafting_from_stash():
    recipes = {
        "t4": CraftRecipe(
            output_id="t4",
            output_count=1,
            ingredients={"t3": 2},
            lmd_cost=100,
        ),
        "t3": CraftRecipe(
            output_id="t3",
            output_count=1,
            ingredients={"t2": 3},
            lmd_cost=10,
        ),
    }

    result = simulate_crafting(
        required={"t4": 1},
        owned={"t2": 6},
        recipes=recipes,
    )

    assert result["remaining"] == {}
    assert result["lmd_crafting"] == 120
    row = result["item_rows"][0]
    assert row["crafted"] == 1


def test_reserved_material_protects_existing_stock_but_allows_new_crafting():
    recipes = {
        "t4": CraftRecipe(
            output_id="t4",
            output_count=1,
            ingredients={"t3": 2},
        ),
    }

    result = simulate_crafting(
        required={"t4": 1},
        owned={"t4": 1, "t3": 99},
        recipes=recipes,
        reserved_items={"t4"},
    )

    # The owned T4 is protected, so none is taken directly from stash.
    assert result["item_rows"][0]["from_stash"] == 0

    # But the planner may create a new T4 from other available resources.
    assert result["item_rows"][0]["crafted"] == 1
    assert result["remaining"] == {}


def test_module_cost_is_specific_to_selected_module():
    current = OperatorState(
        operator_id="char_x",
        name="X",
        elite=2,
        level=60,
        skill_level=7,
        mastery=SkillState(),
        modules={
            "mod_a": ModuleProgress(level=1),
            "mod_b": ModuleProgress(level=0),
        },
    )

    target = UpgradeGoal(
        operator_id="char_x",
        elite=2,
        level=60,
        skill_level=7,
        mastery=SkillState(),
        module_id="mod_b",
        module_level=2,
    )

    model = OperatorCostModel(
        operator_id="char_x",
        name="X",
        rarity=6,
        module_names={
            "mod_a": "A",
            "mod_b": "B",
        },
        module_costs_by_id={
            "mod_a": {
                2: CostBundle(materials={"wrong": 9})
            },
            "mod_b": {
                1: CostBundle(
                    lmd=10,
                    materials={"block": 1},
                ),
                2: CostBundle(
                    lmd=20,
                    materials={"data": 2},
                ),
            },
        },
    )

    result = calculate_upgrade_cost(
        current,
        target,
        model,
        constants={},
        leveling_fn=fake_leveling,
    )

    assert result.lmd == 30
    assert result.materials == {
        "block": 1,
        "data": 2,
    }


def test_hard_current_state_rejects_downgrade():
    current = OperatorState(
        operator_id="char_x",
        name="X",
        elite=2,
        level=60,
        skill_level=7,
    )
    target = UpgradeGoal(
        operator_id="char_x",
        elite=2,
        level=50,
        skill_level=7,
    )
    model = OperatorCostModel(
        operator_id="char_x",
        name="X",
        rarity=6,
    )

    try:
        calculate_upgrade_cost(
            current,
            target,
            model,
            {},
            fake_leveling,
        )
    except ValueError as exc:
        assert "below" in str(exc)
    else:
        raise AssertionError("Expected downgrade validation error.")
