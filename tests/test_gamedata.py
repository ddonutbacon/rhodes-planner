from rhodes.adapters.gamedata import build_operator_cost_model, operator_catalog

def test_character_parser():
    chars = {
        "char_a": {
            "name":"A", "rarity":5, "profession":"SNIPER", "profession":"SNIPER",
            "phases":[{}, {"evolveCost":[{"id":"rock","count":4}]}, {"evolveCost":[{"id":"device","count":5}]}],
            "allSkillLvlup":[{"lvlUpCost":[{"id":"book","count":2}]}],
            "skills":[{"levelUpCostCond":[{"levelUpCost":[{"id":"m","count":3}]}]}]
        }
    }
    cat = operator_catalog(chars)
    assert cat["char_a"]["rarity"] == 6
    model = build_operator_cost_model("char_a", chars, {"equipDict":{}})
    assert model.promotion_costs[1].materials["rock"] == 4
    assert model.skill_rank_costs[2].materials["book"] == 2
    assert model.mastery_costs["s1"][1].materials["m"] == 3


def test_current_tier_string_rarity_parser():
    chars = {
        "char_1": {"name": "One Star", "rarity": "TIER_1", "profession": "SNIPER", "phases": [], "skills": []},
        "char_6": {"name": "Six Star", "rarity": "TIER_6", "profession": "CASTER", "phases": [], "skills": []},
    }

    cat = operator_catalog(chars)

    assert cat["char_1"]["rarity"] == 1
    assert cat["char_6"]["rarity"] == 6


def test_legacy_zero_based_numeric_rarity_parser():
    chars = {
        "char_old": {"name": "Legacy Six Star", "rarity": 5, "profession": "WARRIOR", "phases": [], "skills": []},
    }

    cat = operator_catalog(chars)
    assert cat["char_old"]["rarity"] == 6
