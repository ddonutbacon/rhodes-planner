from rhodes.core.models import Inventory, CostBundle, StageModel, StageDrop
from rhodes.core.planner import calculate_deficit, aggregate_costs
from rhodes.core.farming import build_farming_plan

def test_deficit():
    req = CostBundle(lmd=1000, exp=500, materials={"a":10,"b":2})
    inv = Inventory(lmd=400, exp=900, materials={"a":3,"b":5})
    d = calculate_deficit(req, inv)
    assert d.lmd == 600
    assert d.exp == 0
    assert d.materials == {"a":7}

def test_aggregate():
    a = CostBundle(lmd=100, materials={"x":2})
    b = CostBundle(lmd=50, exp=30, materials={"x":3,"y":1})
    out = aggregate_costs([a,b])
    assert out.lmd == 150
    assert out.exp == 30
    assert out.materials["x"] == 5

def test_farming_selects_best_drop_per_sanity():
    stages = [
        StageModel(stage_id="a", code="A", sanity_cost=10, drops=[StageDrop(item_id="x", expected_per_run=1)]),
        StageModel(stage_id="b", code="B", sanity_cost=20, drops=[StageDrop(item_id="x", expected_per_run=3)]),
    ]
    plan = build_farming_plan(CostBundle(materials={"x":6}), stages)
    assert len(plan.lines) == 1
    assert plan.lines[0].stage_code == "B"
    assert plan.lines[0].runs == 2
    assert plan.total_sanity == 40
