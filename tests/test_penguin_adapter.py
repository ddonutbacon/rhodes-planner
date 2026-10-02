from rhodes.adapters import penguin


def test_penguin_fetch_uses_only_v2_matrix(monkeypatch):
    called = []

    def fake_get_json(url, cache_key, max_age_hours):
        called.append(url)
        return {"matrix": []}

    monkeypatch.setattr(penguin, "get_json", fake_get_json)
    penguin.fetch_penguin_matrix("US")

    assert len(called) == 1
    assert "/v2/result/matrix?server=US" in called[0]
    assert "/stage" not in called[0]
    assert "/items" not in called[0]


def test_matrix_joins_to_static_stage_table():
    matrix = {
        "matrix": [
            {
                "stageId": "main_01-07",
                "itemId": "30012",
                "quantity": 120,
                "times": 100,
            }
        ]
    }

    stage_table = {
        "stages": {
            "main_01-07": {
                "stageId": "main_01-07",
                "code": "1-7",
                "apCost": 6,
            },
            "training": {
                "stageId": "training",
                "code": "TR-X",
                "apCost": 0,
            },
        }
    }

    stages = penguin.normalize_stages(matrix, stage_table)

    assert len(stages) == 1
    assert stages[0].stage_id == "main_01-07"
    assert stages[0].code == "1-7"
    assert stages[0].sanity_cost == 6
    assert stages[0].drops[0].expected_per_run == 1.2


def test_matrix_derives_lmd_and_exp_yield():
    matrix = {
        "matrix": [
            {
                "stageId": "ce_test",
                "itemId": "4001",
                "quantity": 100000,
                "times": 10,
            },
            {
                "stageId": "ce_test",
                "itemId": "2004",
                "quantity": 20,
                "times": 10,
            },
        ]
    }
    stage_table = {
        "stages": {
            "ce_test": {
                "stageId": "ce_test",
                "code": "CE-X",
                "apCost": 36,
            }
        }
    }

    stages = penguin.normalize_stages(matrix, stage_table)
    assert stages[0].lmd_per_run == 10000
    assert stages[0].exp_per_run == 4000


def test_ce6_ls6_fallback_yields():
    matrix = {"matrix": []}
    stage_table = {
        "stages": {
            "ce6": {"stageId": "ce6", "code": "CE-6", "apCost": 36},
            "ls6": {"stageId": "ls6", "code": "LS-6", "apCost": 36},
        }
    }

    stages = penguin.normalize_stages(matrix, stage_table)
    by_code = {s.code: s for s in stages}

    assert by_code["CE-6"].lmd_per_run == 10000
    assert by_code["LS-6"].exp_per_run == 10000
