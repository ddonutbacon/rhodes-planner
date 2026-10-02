from rhodes.adapters.penguin_export import (
    build_penguin_planner_config_payload,
    exp_points_to_card_needs,
)
from rhodes.core.models import Inventory


def test_penguin_planner_config_matches_import_schema_and_incremental_farm_delta():
    inv = Inventory(
        lmd=1_477_496,
        exp_cards={"2004": 156, "2003": 1003},
        materials={
            "2004": 156,
            "2003": 1003,
            "30012": 325,
            "3243": 0,
        },
    )

    payload = build_penguin_planner_config_payload(
        inventory=inv,
        # Rhodes has already determined that 5 additional Orirock Cubes and
        # 4 additional Sniper Dualchips must be obtained.
        farm_targets={"30012": 5, "3243": 4},
        additional_lmd=100_000,
        additional_exp=5_600,
        item_meta={},
    )

    assert payload["@type"] == "@penguin-statistics/planner/config"
    assert all(set(row) == {"id", "need", "have"} for row in payload["items"])

    by_id = {row["id"]: row for row in payload["items"]}

    # `need` is absolute in Penguin, so it must be current have + the amount
    # Rhodes still wants farmed. This prevents Penguin from subtracting stash
    # for a second time.
    assert by_id["30012"] == {"id": "30012", "need": 330, "have": 325}
    assert by_id["3243"] == {"id": "3243", "need": 4, "have": 0}
    assert by_id["4001"] == {
        "id": "4001",
        "need": 1_577_496,
        "have": 1_477_496,
    }

    # 5,600 EXP -> +2 T4, +1 T3, +1 T2, +1 T1.
    assert by_id["2004"]["need"] == 158
    assert by_id["2004"]["have"] == 156
    assert by_id["2003"]["need"] == 1004
    assert by_id["2003"]["have"] == 1003


def test_reserved_high_tier_chain_exports_lower_tier_farm_target_even_if_owned():
    inv = Inventory(
        materials={
            # User owns plenty of the T3 ingredient, but Rhodes' reserve policy
            # says the reserved T4/T5 chain must be farmed anew.
            "t3": 100,
            "t4": 20,
        }
    )

    payload = build_penguin_planner_config_payload(
        inventory=inv,
        farm_targets={"t3": 6},
        additional_lmd=0,
        additional_exp=0,
        item_meta={
            "t3": {"name": "Example T3"},
            "t4": {"name": "Example T4"},
        },
    )

    by_id = {row["id"]: row for row in payload["items"]}

    # Penguin sees a 6-item deficit despite the 100 already owned.
    assert by_id["t3"] == {"id": "t3", "need": 106, "have": 100}

    # The original high-tier row is not given a new need; Rhodes already
    # translated that requirement into its effective farm inputs.
    assert by_id["t4"] == {"id": "t4", "need": 0, "have": 20}


def test_exp_points_convert_to_t4_first_battle_records():
    needs = exp_points_to_card_needs(5600)
    assert needs == {
        "2001": 1,
        "2002": 1,
        "2003": 1,
        "2004": 2,
    }
