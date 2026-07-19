from datetime import datetime

from pydantic import BaseModel, Field

from app.contracts.enums import SourceType


class RawSignal(BaseModel):
    """Thin pre-Evidence shape produced by sourcing connectors."""

    source_type: SourceType
    source_ref: str
    content: str
    observed_at: datetime | None = None
    founder_hint: str | None = None  # name/handle hint for entity resolution
    company_hint: str | None = None


class ConnectorQuery(BaseModel):
    params: dict = Field(default_factory=dict)
