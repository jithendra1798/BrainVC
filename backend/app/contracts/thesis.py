from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from app.contracts.enums import RiskPosture, Stage


class AxisWeights(BaseModel):
    """Emphasis in the recommendation logic only — axes are NEVER averaged into one number."""

    founder: float = 1.0
    market: float = 1.0
    idea_vs_market: float = 1.0


class ThesisConfig(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    name: str
    sectors: list[str]
    stages: list[Stage]
    geographies: list[str]
    check_size_usd: int = 100_000
    ownership_target_pct: float | None = None
    risk_posture: RiskPosture = RiskPosture.BALANCED
    axis_weights: AxisWeights = Field(default_factory=AxisWeights)
