from rhodes.adapters.arkprts_export import parse_arkprts_full_export


def test_full_export_parser():
    payload = {
        "status": {
            "level": 100,
            "serverName": "Terra",
            "gold": 123456,
            "diamondShard": 12000,
            "freeDiamond": 20,
            "payDiamond": 3,
        },
        "inventory": {
            "2001": 2,
            "2002": 3,
            "2003": 4,
            "2004": 5,
            "30012": 9,
        },
        "troop": {
            "chars": {
                "1": {
                    "charId": "char_test",
                    "potentialRank": 4,
                    "mainSkillLvl": 7,
                    "level": 60,
                    "evolvePhase": 2,
                    "skills": [
                        {"specializeLevel": 0},
                        {"specializeLevel": 1},
                        {"specializeLevel": 3},
                    ],
                    "currentEquip": "uniequip_test",
                    "equip": {
                        "uniequip_test": {
                            "hide": 0,
                            "locked": 0,
                            "level": 2,
                        }
                    },
                }
            },
            "spOperator": {},
        },
        "dungeon": {"stages": {"main_01-07": {}}},
    }

    inv, ops, meta = parse_arkprts_full_export(payload)

    assert inv.lmd == 123456
    assert inv.orundum == 12000
    assert inv.originite_prime == 23
    assert inv.exp == 2*200 + 3*400 + 4*1000 + 5*2000
    assert inv.exp_cards["2004"] == 5

    op = ops["char_test"]
    assert op.elite == 2
    assert op.level == 60
    assert op.skill_level == 7
    assert op.mastery.s3 == 3
    assert op.module_level == 2
    assert op.modules["uniequip_test"].level == 2
    assert op.potential_rank == 4

    assert meta["operator_count"] == 1
    assert meta["stage_record_count"] == 1


def test_template_operator_parser():
    payload = {
        "status": {"gold": 0, "diamondShard": 0, "freeDiamond": 0, "payDiamond": 0},
        "inventory": {},
        "troop": {
            "chars": {
                "1": {
                    "charId": "char_template",
                    "mainSkillLvl": 7,
                    "level": 20,
                    "evolvePhase": 2,
                    "skills": [],
                    "equip": {},
                    "currentEquip": None,
                    "currentTmpl": "char_template_form",
                    "tmpl": {
                        "char_template_form": {
                            "skills": [
                                {"specializeLevel": 1},
                                {"specializeLevel": 2},
                                {"specializeLevel": 3},
                            ],
                            "currentEquip": "uniequip_form",
                            "equip": {
                                "uniequip_form": {
                                    "hide": 0,
                                    "locked": 0,
                                    "level": 3,
                                }
                            },
                        }
                    },
                }
            }
        },
    }

    _, ops, _ = parse_arkprts_full_export(payload)
    op = ops["char_template"]

    assert op.mastery.s1 == 1
    assert op.mastery.s2 == 2
    assert op.mastery.s3 == 3
    assert op.current_module_id == "uniequip_form"
    assert op.module_level == 3
    assert "char_template_form" in op.forms
