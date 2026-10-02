from __future__ import annotations

import math
from typing import List

from .models import CostBundle, StageModel, FarmingLine, FarmingPlan


def best_stage_for_item(item_id: str, stages: List[StageModel]):
    candidates = []

    for stage in stages:
        for drop in stage.drops:
            if drop.item_id == item_id and drop.expected_per_run > 0:
                candidates.append(
                    (
                        drop.expected_per_run / stage.sanity_cost,
                        stage,
                        drop.expected_per_run,
                    )
                )

    return max(candidates, key=lambda x: x[0]) if candidates else None


def _preferred_resource_stage(
    stages: List[StageModel],
    resource: str,
):
    if resource == "LMD":
        exact_code = "CE-6"
        prefix = "CE-"
        yield_attr = "lmd_per_run"
    elif resource == "EXP":
        exact_code = "LS-6"
        prefix = "LS-"
        yield_attr = "exp_per_run"
    else:
        return None

    exact = next(
        (
            s for s in stages
            if s.code == exact_code and getattr(s, yield_attr) > 0
        ),
        None,
    )

    if exact:
        return exact

    supply = [
        s for s in stages
        if s.code.startswith(prefix) and getattr(s, yield_attr) > 0
    ]

    if supply:
        return max(
            supply,
            key=lambda s: getattr(s, yield_attr) / s.sanity_cost,
        )

    generic = [
        s for s in stages
        if getattr(s, yield_attr) > 0
    ]

    return max(
        generic,
        key=lambda s: getattr(s, yield_attr) / s.sanity_cost,
    ) if generic else None


def build_farming_plan(
    deficit: CostBundle,
    stages: List[StageModel],
) -> FarmingPlan:
    lines = []

    for item_id, amount_needed in sorted(deficit.materials.items()):
        best = best_stage_for_item(item_id, stages)

        if not best:
            continue

        _, stage, rate = best
        runs = math.ceil(amount_needed / rate)

        lines.append(
            FarmingLine(
                stage_code=stage.code,
                stage_id=stage.stage_id,
                runs=runs,
                sanity=runs * stage.sanity_cost,
                purpose=item_id,
                expected_output=runs * rate,
            )
        )

    if deficit.lmd > 0:
        stage = _preferred_resource_stage(stages, "LMD")

        if stage:
            runs = math.ceil(deficit.lmd / stage.lmd_per_run)

            lines.append(
                FarmingLine(
                    stage_code=stage.code,
                    stage_id=stage.stage_id,
                    runs=runs,
                    sanity=runs * stage.sanity_cost,
                    purpose="LMD",
                    expected_output=runs * stage.lmd_per_run,
                )
            )

    if deficit.exp > 0:
        stage = _preferred_resource_stage(stages, "EXP")

        if stage:
            runs = math.ceil(deficit.exp / stage.exp_per_run)

            lines.append(
                FarmingLine(
                    stage_code=stage.code,
                    stage_id=stage.stage_id,
                    runs=runs,
                    sanity=runs * stage.sanity_cost,
                    purpose="EXP",
                    expected_output=runs * stage.exp_per_run,
                )
            )

    return FarmingPlan(
        lines=lines,
        total_sanity=sum(x.sanity for x in lines),
    )
