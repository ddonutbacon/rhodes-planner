from rhodes.adapters.gamedata import build_item_metadata_map, operator_catalog


def test_future_operator_uses_appellation_when_en_missing():
    cn = {
        "char_999_future": {
            "name": "未来干员",
            "appellation": "Future Operator",
            "profession": "SNIPER",
            "rarity": "TIER_6",
        }
    }
    catalog = operator_catalog(cn, {})
    assert catalog["char_999_future"]["name"] == "Future Operator"
    assert catalog["char_999_future"]["available_on_en"] is False


def test_cn_only_material_alias_is_english():
    cn_items = {
        "items": {
            "future_mat": {
                "name": "电极单元",
                "iconId": "future_mat",
                "rarity": "TIER_3",
            }
        }
    }
    meta = build_item_metadata_map(cn_items, {"items": {}})
    assert meta["future_mat"]["name"] == "Electrode Unit"
    assert meta["future_mat"]["cn_name"] == "电极单元"
