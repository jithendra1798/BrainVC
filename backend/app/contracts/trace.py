from datetime import datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from app.contracts.entities import utcnow


class TraceEntry(BaseModel):
    """Step-level chain-of-thought log. Every module writes these on entry/exit."""

    id: UUID = Field(default_factory=uuid4)
    opportunity_id: UUID | None = None
    module: str  # "sourcing.inbound_deck", "scoring.founder", "validation", ...
    step: str
    input_refs: list[UUID] = Field(default_factory=list)
    output_refs: list[UUID] = Field(default_factory=list)
    model: str | None = None  # LLM model used, if any
    summary: str = ""
    created_at: datetime = Field(default_factory=utcnow)
