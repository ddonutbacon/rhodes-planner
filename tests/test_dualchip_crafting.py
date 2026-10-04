from rhodes.core.crafting import (
    add_dualchip_factory_recipes,
    simulate_crafting,
)


def _meta():
    return {
        "dual_sniper": {"name": "Sniper Dualchip", "rarity": "TIER_5"},
        "pack_sniper": {"name": "Sniper Chip Pack", "rarity": "TIER_4"},
        "catalyst": {"name": "Chip Catalyst", "rarity": "TIER_4"},
        "dual_medic": {"name": "Medic Dualchip", "rarity": "TIER_5"},
        "pack_medic": {"name": "Medic Chip Pack", "rarity": "TIER_4"},
    }


def test_dualchip_recipe_is_added_from_item_names():
    recipes = add_dualchip_factory_recipes({}, _meta())
    recipe = recipes["dual_sniper"]
    assert recipe.output_count == 1
    assert recipe.ingredients == {"pack_sniper": 2, "catalyst": 1}


def test_owned_chip_packs_and_catalysts_cover_dualchip_requirement():
    recipes = add_dualchip_factory_recipes({}, _meta())
    result = simulate_crafting(
        required={"dual_sniper": 4},
        owned={"pack_sniper": 8, "catalyst": 4},
        recipes=recipes,
    )
    assert result["remaining"] == {}
    row = result["item_rows"][0]
    assert row["from_stash"] == 0
    assert row["crafted"] == 4
    assert row["remaining"] == 0
    assert result["stock_after"]["pack_sniper"] == 0
    assert result["stock_after"]["catalyst"] == 0


def test_partial_dualchip_coverage_only_leaves_true_shortfall():
    recipes = add_dualchip_factory_recipes({}, _meta())
    result = simulate_crafting(
        required={"dual_sniper": 5},
        owned={"dual_sniper": 2, "pack_sniper": 4, "catalyst": 3},
        recipes=recipes,
    )
    assert result["remaining"] == {"dual_sniper": 1.0}
    row = result["item_rows"][0]
    assert row["from_stash"] == 2
    assert row["crafted"] == 2
    assert row["remaining"] == 1
    # Two crafts consume four packs and two catalysts; one catalyst remains.
    assert result["stock_after"]["pack_sniper"] == 0
    assert result["stock_after"]["catalyst"] == 1


def test_dualchip_crafting_competes_for_shared_catalysts():
    recipes = add_dualchip_factory_recipes({}, _meta())
    result = simulate_crafting(
        required={"dual_sniper": 2, "dual_medic": 2},
        owned={
            "pack_sniper": 4,
            "pack_medic": 4,
            "catalyst": 2,
        },
        recipes=recipes,
    )
    # Only two total Dualchips can be crafted because the catalyst pool is shared.
    assert sum(result["remaining"].values()) == 2
    assert result["stock_after"]["catalyst"] == 0
