from rhodes.adapters.arkprts_export import parse_arkprts_full_export


def test_parser_keeps_planning_state_without_identity_fields():
    payload = {
        "status": {
            "gold": 12345,
            "diamondShard": 6000,
            "freeDiamond": 10,
            "payDiamond": 2,
            "level": 100,
            "serverName": "Terra",
            "nickName": "PRIVATE",
            "uid": "PRIVATE-UID",
        },
        "inventory": {"2003": 5, "3001": 7, "7003": 3, "7004": 1},
        "troop": {
            "chars": {
                "1": {
                    "charId": "char_test",
                    "evolvePhase": 2,
                    "level": 60,
                    "mainSkillLvl": 7,
                    "skills": [],
                    "equip": {},
                }
            }
        },
        "dungeon": {"stages": {}},
    }
    inv, ops, meta = parse_arkprts_full_export(payload)
    assert inv.lmd == 12345
    assert not hasattr(inv, "orundum")
    assert not hasattr(inv, "originite_prime")
    assert inv.materials["7003"] == 3
    assert inv.materials["7004"] == 1
    assert "char_test" in ops
    assert "uid" not in meta
    assert "nickname" not in meta
    assert "PRIVATE" not in str(meta)
