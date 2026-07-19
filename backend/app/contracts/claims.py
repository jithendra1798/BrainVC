from datetime import datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from app.contracts.entities import utcnow
from app.contracts.enums import ClaimCategory, ClaimStatus, Relation, TrustLevel


class TrustScore(BaseModel):
    value: float = 0.2  # 0.0–1.0; claims are born skeptical
    level: TrustLevel = TrustLevel.LOW
    rationale: str = "extracted, not yet validated"
    verification_method: str = "single-source, unverified"


class EvidenceLink(BaseModel):
    evidence_id: UUID
    relation: Relation


class Claim(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    opportunity_id: UUID
    category: ClaimCategory
    text: str  # atomic, checkable assertion
    status: ClaimStatus = ClaimStatus.UNVERIFIED
    trust: TrustScore = Field(default_factory=TrustScore)
    evidence_links: list[EvidenceLink] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utcnow)


class ContradictionFlag(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    claim_id: UUID
    conflicting_evidence_id: UUID
    note: str
    created_at: datetime = Field(default_factory=utcnow)
