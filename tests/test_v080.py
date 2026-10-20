from rhodes.core.models import Inventory, OperatorState
from rhodes.core.v080 import (
    active_goal_pairs,
    merge_import_preserving_manual,
    move_list_item,
    resolve_special_acquisitions,
    spendable_inventory,
)


def test_partial_reserve():
    inv = Inventory(lmd=1000, exp=5000, materials={"a": 30})
    out = spendable_inventory(
        inv,
        reserved_materials={"a": 10},
        reserved_lmd=250,
        reserved_exp=1000,
    )
    assert out.lmd == 750
    assert out.exp == 4000
    assert out.materials["a"] == 20


def test_active_goal_pairs():
    goals = [
        {"operator_id": "a", "active": True},
        {"operator_id": "b", "active": False},
        {"operator_id": "c"},
    ]
    costs = [{"x": 1}, {"x": 2}, {"x": 3}]
    pairs = active_goal_pairs(goals, costs)
    assert [g["operator_id"] for g, _ in pairs] == ["a", "c"]


def test_move_list_item():
    assert move_list_item(["a", "b", "c"], 1, -1) == ["b", "a", "c"]
    assert move_list_item(["a", "b", "c"], 0, -1) == ["a", "b", "c"]


def test_merge_preserves_manual_operator_override():
    old_op = OperatorState(operator_id="x", name="X", elite=1, level=20)
    manual_op = OperatorState(operator_id="x", name="X", elite=2, level=60)
    new_import_op = OperatorState(operator_id="x", name="X", elite=1, level=40)

    old_inv = Inventory(lmd=100, materials={"m": 5})
    current_inv = Inventory(lmd=150, materials={"m": 5})
    new_inv = Inventory(lmd=200, materials={"m": 8})

    old_snapshot = {
        "inventory": old_inv.model_dump(),
        "operators": {"x": old_op.model_dump()},
    }

    merged_inv, merged_ops, info = merge_import_preserving_manual(
        current_inventory=current_inv,
        current_operators={"x": manual_op},
        previous_snapshot=old_snapshot,
        imported_inventory=new_inv,
        imported_operators={"x": new_import_op},
    )

    assert merged_inv.lmd == 150
    assert merged_inv.materials["m"] == 8
    assert merged_ops["x"].elite == 2
    assert merged_ops["x"].level == 60
    assert info["preserved_operator_overrides"] == 1



def test_chip_catalyst_resolves_to_purchase_certificates():
    inv = Inventory(materials={"4006": 45})
    targets, notes = resolve_special_acquisitions({"32001": 2}, inv)
    assert "32001" not in targets
    assert targets["4006"] == 135
    assert notes[0]["source_quantity"] == 2
    assert notes[0]["currency_required"] == 180
    assert notes[0]["currency_owned"] == 45


def test_chip_catalyst_no_ap_farm_when_certificates_already_cover_it():
    inv = Inventory(materials={"4006": 180})
    targets, notes = resolve_special_acquisitions({"32001": 2}, inv)
    assert "32001" not in targets
    assert "4006" not in targets
    assert notes[0]["currency_to_farm"] == 0
