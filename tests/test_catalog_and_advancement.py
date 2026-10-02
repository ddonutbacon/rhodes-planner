
from rhodes.adapters.gamedata import (
    advancement_item_ids,
    operator_catalog,
)


def test_catalog_keeps_canonical_operator_professions_only():
    chars = {
        "char_real": {
            "name": "Real Operator",
            "rarity": "TIER_6",
            "profession": "CASTER",
        },
        "char_story": {
            "name": "Story Character",
            "rarity": "TIER_6",
            "profession": "TRAP",
        },
    }

    catalog = operator_catalog(chars)

    assert "char_real" in catalog
    assert catalog["char_real"]["class"] == "Caster"
    assert "char_story" not in catalog


def test_advancement_items_are_derived_from_actual_upgrade_costs():
    chars = {
        "char_real": {
            "name": "Real Operator",
            "rarity": "TIER_6",
            "profession": "SNIPER",
            "phases": [
                {},
                {"evolveCost": [{"id": "rock", "count": 4}]},
            ],
            "allSkillLvlup": [
                {"lvlUpCost": [{"id": "book", "count": 2}]},
            ],
            "skills": [],
        },
        "char_story": {
            "name": "Story",
            "rarity": "TIER_6",
            "profession": "TRAP",
            "phases": [
                {},
                {"evolveCost": [{"id": "story_token", "count": 99}]},
            ],
            "allSkillLvlup": [],
            "skills": [],
        },
    }

    item_meta = {
        "rock": {"rarity": "TIER_3"},
        "book": {"rarity": "TIER_2"},
        "story_token": {"rarity": "TIER_5"},
    }

    ids = advancement_item_ids(
        chars,
        {"equipDict": {}},
        item_meta,
    )

    assert ids == {"rock", "book"}
