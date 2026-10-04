from rhodes.adapters.gamedata import operator_catalog, build_item_metadata_map
from rhodes.core.crafting import CraftRecipe, expand_high_tier_farm_targets
from rhodes.core.farming import best_stage_for_item
from rhodes.core.models import StageDrop, StageModel


def test_cn_operator_is_kept_when_absent_from_en():
    cn = {
        "char_future": {
            "name": "未来干员",
            "profession": "CASTER",
            "rarity": "TIER_6",
        }
    }
    catalog = operator_catalog(cn, {})
    assert "char_future" in catalog
    assert catalog["char_future"]["availability"] == "CN only"
    assert catalog["char_future"]["available_on_en"] is False


def test_en_name_wins_for_released_operator():
    cn = {
        "char_test": {
            "name": "中文名",
            "profession": "SNIPER",
            "rarity": "TIER_5",
        }
    }
    en = {
        "char_test": {
            "name": "English Name",
            "profession": "SNIPER",
            "rarity": "TIER_5",
        }
    }
    catalog = operator_catalog(cn, en)
    assert catalog["char_test"]["name"] == "English Name"
    assert catalog["char_test"]["availability"] == "EN"


def test_future_material_chain_expands_to_new_t3_component():
    item_meta = {
        "T5Y": {"rarity": "TIER_5"},
        "T4A": {"rarity": "TIER_4"},
        "T3Z": {"rarity": "TIER_3"},
    }
    recipes = {
        "T5Y": CraftRecipe("T5Y", 1, {"T4A": 2}),
        "T4A": CraftRecipe("T4A", 1, {"T3Z": 3}),
    }
    out = expand_high_tier_farm_targets(
        {"T5Y": 2}, {}, recipes, item_meta, stop_tier=3
    )
    assert out["farm_targets"] == {"T3Z": 12.0}


def test_existing_stage_can_gain_new_drop_without_code_change():
    stage = StageModel(
        stage_id="main_test",
        code="10-8",
        sanity_cost=18,
        drops=[StageDrop(item_id="NEW", expected_per_run=0.5)],
    )
    best = best_stage_for_item("NEW", [stage])
    assert best is not None
    assert best[1].code == "10-8"


def test_material_availability_can_be_derived_from_en_snapshot():
    cn_items = {"items": {"NEW": {"name": "新素材", "rarity": "TIER_3"}}}
    en_items = {"items": {}}
    cn_meta = build_item_metadata_map(cn_items)
    en_meta = build_item_metadata_map(en_items)
    assert "NEW" in cn_meta
    assert "NEW" not in en_meta


def test_penguin_matrix_can_add_new_drop_to_existing_stage():
    from rhodes.adapters.penguin import normalize_stages

    matrix = {
        "matrix": [
            {"stageId": "main_test", "itemId": "OLD", "times": 100, "quantity": 50},
            {"stageId": "main_test", "itemId": "NEW", "times": 100, "quantity": 20},
        ]
    }
    stage_table = {
        "stages": {
            "main_test": {
                "stageId": "main_test",
                "code": "10-8",
                "apCost": 18,
            }
        }
    }
    stages = normalize_stages(matrix, stage_table)
    assert len(stages) == 1
    drops = {drop.item_id: drop.expected_per_run for drop in stages[0].drops}
    assert drops["OLD"] == 0.5
    assert drops["NEW"] == 0.2


def test_future_operator_cost_model_keeps_new_material_id():
    from rhodes.adapters.gamedata import build_operator_cost_model

    chars = {
        "char_future": {
            "name": "未来干员",
            "profession": "CASTER",
            "rarity": "TIER_6",
            "phases": [
                {},
                {"evolveCost": [{"id": "T3Z", "count": 5, "type": "MATERIAL"}]},
                {"evolveCost": [{"id": "T5Y", "count": 4, "type": "MATERIAL"}]},
            ],
            "allSkillLvlup": [],
            "skills": [],
        }
    }
    model = build_operator_cost_model("char_future", chars, {"equipDict": {}})
    assert model.promotion_costs[1].materials["T3Z"] == 5
    assert model.promotion_costs[2].materials["T5Y"] == 4
