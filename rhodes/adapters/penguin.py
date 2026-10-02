from __future__ import annotations

from collections import defaultdict
from typing import List

from .http import get_json
from rhodes.core.models import StageDrop, StageModel

MATRIX_URL = "https://penguin-stats.io/PenguinStats/api/v2/result/matrix"

EXP_CARD_VALUES = {
    "2001": 200,
    "2002": 400,
    "2003": 1000,
    "2004": 2000,
}


def fetch_penguin_matrix(server: str = "US"):
    return get_json(
        f"{MATRIX_URL}?server={server}&show_closed_zones=false",
        f"penguin_matrix_{server}",
        6,
    )


def normalize_stages(matrix_raw, stage_table_raw) -> List[StageModel]:
    matrix = matrix_raw.get(
        "matrix",
        matrix_raw if isinstance(matrix_raw, list) else [],
    )

    if isinstance(stage_table_raw, dict):
        stages_obj = stage_table_raw.get("stages", stage_table_raw)
    else:
        stages_obj = {}

    by_stage = defaultdict(list)
    lmd_by_stage = defaultdict(float)
    exp_by_stage = defaultdict(float)

    for row in matrix:
        if not isinstance(row, dict):
            continue

        stage_id = str(row.get("stageId") or "")
        item_id = str(row.get("itemId") or "")
        times = row.get("times", 0) or 0
        qty = row.get("quantity", 0) or 0

        if not stage_id or not item_id or times <= 0:
            continue

        rate = float(qty) / float(times)

        by_stage[stage_id].append(
            StageDrop(
                item_id=item_id,
                expected_per_run=rate,
            )
        )

        if item_id == "4001":
            lmd_by_stage[stage_id] += rate

        if item_id in EXP_CARD_VALUES:
            exp_by_stage[stage_id] += rate * EXP_CARD_VALUES[item_id]

    out: List[StageModel] = []

    if isinstance(stages_obj, dict):
        iterable = stages_obj.items()
    elif isinstance(stages_obj, list):
        iterable = (
            (str(s.get("stageId") or ""), s)
            for s in stages_obj
            if isinstance(s, dict)
        )
    else:
        iterable = []

    for fallback_id, row in iterable:
        if not isinstance(row, dict):
            continue

        stage_id = str(row.get("stageId") or fallback_id or "")
        code = str(row.get("code") or stage_id)
        ap_cost = int(row.get("apCost") or 0)

        if not stage_id or ap_cost <= 0:
            continue

        if stage_id not in by_stage and code not in {"CE-6", "LS-6"}:
            continue

        lmd = lmd_by_stage[stage_id]
        exp = exp_by_stage[stage_id]

        if code == "CE-6" and lmd <= 0:
            lmd = 10000.0

        if code == "LS-6" and exp <= 0:
            exp = 10000.0

        out.append(
            StageModel(
                stage_id=stage_id,
                code=code,
                sanity_cost=ap_cost,
                drops=by_stage.get(stage_id, []),
                lmd_per_run=lmd,
                exp_per_run=exp,
            )
        )

    return out
