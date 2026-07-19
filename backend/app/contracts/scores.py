from datetime import datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from app.contracts.entities import utcnow
from app.contracts.enums import Axis, Stance, Trend


class ConfidenceBand(BaseModel):
    low: float
    high: float
    basis: str  # honest label, e.g. "heuristic — evidence coverage + k-sample agreement"


class AxisScore(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    opportunity_id: UUID
    thesis_id: UUID  # same founder scores differently under a different thesis
    axis: Axis  # FOUNDER | MARKET | IDEA_VS_MARKET — independent, never averaged
    score: float  # 0–100
    confidence: ConfidenceBand
    trend: Trend = Trend.INSUFFICIENT_HISTORY
    market_stance: Stance | None = None  # market axis only
    rationale: str = ""
    evidence_ids: list[UUID] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utcnow)


class FounderScoreEntry(BaseModel):
    """Append-only 'credit score for founders'. Keyed by PERSON, not opportunity."""

    id: UUID = Field(default_factory=uuid4)
    founder_id: UUID
    score: float  # 0–100
    confidence: ConfidenceBand
    inputs: dict = Field(default_factory=dict)  # which signals contributed (audit)
    created_at: datetime = Field(default_factory=utcnow)


class DimensionScore(BaseModel):
    score: float  # 0–100
    rationale: str
    evidence_ids: list[UUID] = Field(default_factory=list)


class ColdStartAssessment(BaseModel):
    """Founder potential from public footprint alone. Feeds the FOUNDER axis."""

    founder_id: UUID
    dimension_scores: dict[str, DimensionScore]  # shipping_velocity, technical_depth, ...
    aggregate: float
    confidence: ConfidenceBand
    evidence_ids: list[UUID] = Field(default_factory=list)
    known_unknowns: list[str] = Field(default_factory=list)  # what we could NOT observe
