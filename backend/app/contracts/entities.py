from datetime import datetime, timezone
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from app.contracts.enums import PipelineStatus, Stage, Track


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class FounderRecord(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    canonical_name: str
    handles: dict[str, str] = Field(default_factory=dict)  # {"github": "...", "linkedin": "..."}
    emails: list[str] = Field(default_factory=list)
    bio: str | None = None
    first_seen_at: datetime = Field(default_factory=utcnow)
    # FounderScore is NOT embedded — it lives in Memory as append-only history
    # keyed by founder_id, so it persists across applications and never resets.


class CompanyRecord(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    name: str
    founder_ids: list[UUID] = Field(default_factory=list)
    sector: str | None = None
    geography: str | None = None
    stage: Stage | None = None
    one_liner: str | None = None


class Opportunity(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    company_id: UUID
    track: Track
    status: PipelineStatus = PipelineStatus.SOURCED
    created_at: datetime = Field(default_factory=utcnow)
