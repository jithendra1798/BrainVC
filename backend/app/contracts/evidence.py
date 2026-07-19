from datetime import datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from app.contracts.entities import utcnow
from app.contracts.enums import SourceType


class Evidence(BaseModel):
    """Verbatim excerpt with provenance. Nothing enters the system without one."""

    id: UUID = Field(default_factory=uuid4)
    founder_id: UUID | None = None
    opportunity_id: UUID | None = None
    source_type: SourceType
    source_ref: str  # URL, "deck.pdf#slide=4", or connector-specific locator
    content: str  # raw excerpt — verbatim, never paraphrased
    content_hash: str  # sha256 of normalized content, for dedup
    retrieved_at: datetime = Field(default_factory=utcnow)  # when WE fetched it
    observed_at: datetime | None = None  # when the underlying event happened (trends)
