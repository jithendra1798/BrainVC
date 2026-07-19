from datetime import datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from app.contracts.entities import utcnow
from app.contracts.enums import Recommendation, SectionKind


class MemoSection(BaseModel):
    kind: SectionKind
    markdown: str  # inline [claim:UUID] tokens the UI resolves to trust badges


class Memo(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    opportunity_id: UUID
    thesis_id: UUID
    recommendation: Recommendation
    recommendation_rationale: str = ""
    sections: list[MemoSection]
    claim_ids: list[UUID] = Field(default_factory=list)
    gaps: list[str] = Field(default_factory=list)  # "Cap table: not disclosed" — never fabricated
    created_at: datetime = Field(default_factory=utcnow)
