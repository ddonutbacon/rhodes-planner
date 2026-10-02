from __future__ import annotations
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class CostBundle(BaseModel):
    lmd: int = 0
    exp: int = 0
    materials: Dict[str, float] = Field(default_factory=dict)

    def add(self, other: "CostBundle") -> "CostBundle":
        self.lmd += other.lmd
        self.exp += other.exp
        for k, v in other.materials.items():
            self.materials[k] = self.materials.get(k, 0) + v
        return self


class Inventory(BaseModel):
    lmd: int = Field(default=0, ge=0)
    exp: int = Field(default=0, ge=0)
    exp_cards: Dict[str, int] = Field(default_factory=dict)
    orundum: int = Field(default=0, ge=0)
    originite_prime: int = Field(default=0, ge=0)
    materials: Dict[str, float] = Field(default_factory=dict)


class SkillState(BaseModel):
    s1: int = Field(default=0, ge=0, le=3)
    s2: int = Field(default=0, ge=0, le=3)
    s3: int = Field(default=0, ge=0, le=3)


class ModuleProgress(BaseModel):
    level: int = Field(default=0, ge=0, le=3)
    locked: bool = False
    hidden: bool = False


class OperatorState(BaseModel):
    operator_id: str
    name: str
    rarity: int = Field(default=6, ge=1, le=6)
    elite: int = Field(default=0, ge=0, le=2)
    level: int = Field(default=1, ge=1)
    skill_level: int = Field(default=1, ge=1, le=7)
    mastery: SkillState = Field(default_factory=SkillState)
    module_level: int = Field(default=0, ge=0, le=3)  # active-module compatibility
    current_module_id: Optional[str] = None
    modules: Dict[str, ModuleProgress] = Field(default_factory=dict)
    potential_rank: int = Field(default=0, ge=0)
    forms: Dict[str, Any] = Field(default_factory=dict)


class UpgradeGoal(BaseModel):
    operator_id: str
    elite: int = Field(ge=0, le=2)
    level: int = Field(ge=1)
    skill_level: int = Field(ge=1, le=7)
    mastery: SkillState = Field(default_factory=SkillState)
    module_id: Optional[str] = None
    module_level: int = Field(default=0, ge=0, le=3)


class OperatorCostModel(BaseModel):
    operator_id: str
    name: str
    rarity: int
    promotion_costs: Dict[int, CostBundle] = Field(default_factory=dict)
    skill_rank_costs: Dict[int, CostBundle] = Field(default_factory=dict)
    mastery_costs: Dict[str, Dict[int, CostBundle]] = Field(default_factory=dict)
    module_names: Dict[str, str] = Field(default_factory=dict)
    module_costs_by_id: Dict[str, Dict[int, CostBundle]] = Field(default_factory=dict)


class StageDrop(BaseModel):
    item_id: str
    expected_per_run: float


class StageModel(BaseModel):
    stage_id: str
    code: str
    sanity_cost: int
    drops: List[StageDrop] = Field(default_factory=list)
    lmd_per_run: float = 0
    exp_per_run: float = 0


class FarmingLine(BaseModel):
    stage_code: str
    stage_id: str
    purpose: str
    runs: int
    sanity: int
    expected_output: float


class FarmingPlan(BaseModel):
    lines: List[FarmingLine] = Field(default_factory=list)
    total_sanity: int = 0
