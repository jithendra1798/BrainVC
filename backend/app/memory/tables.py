from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def now() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class ThesisRow(Base):
    __tablename__ = "theses"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    config: Mapped[dict] = mapped_column(JSON)
    is_active: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class FounderRow(Base):
    __tablename__ = "founders"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    canonical_name: Mapped[str] = mapped_column(String(200))
    handles: Mapped[dict] = mapped_column(JSON, default=dict)
    emails: Mapped[list] = mapped_column(JSON, default=list)
    bio: Mapped[str | None] = mapped_column(Text, nullable=True)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class CompanyRow(Base):
    __tablename__ = "companies"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    sector: Mapped[str | None] = mapped_column(String(100), nullable=True)
    geography: Mapped[str | None] = mapped_column(String(100), nullable=True)
    stage: Mapped[str | None] = mapped_column(String(30), nullable=True)
    one_liner: Mapped[str | None] = mapped_column(Text, nullable=True)


class FounderCompanyRow(Base):
    __tablename__ = "founder_companies"
    founder_id: Mapped[str] = mapped_column(ForeignKey("founders.id"), primary_key=True)
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), primary_key=True)
    role: Mapped[str] = mapped_column(String(50), default="founder")


class OpportunityRow(Base):
    __tablename__ = "opportunities"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"))
    track: Mapped[str] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(30))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class EvidenceRow(Base):
    __tablename__ = "evidence"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    founder_id: Mapped[str | None] = mapped_column(ForeignKey("founders.id"), nullable=True)
    opportunity_id: Mapped[str | None] = mapped_column(ForeignKey("opportunities.id"), nullable=True)
    source_type: Mapped[str] = mapped_column(String(30))
    source_ref: Mapped[str] = mapped_column(Text)
    content: Mapped[str] = mapped_column(Text)
    content_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    embedding: Mapped[list | None] = mapped_column(JSON, nullable=True)
    retrieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    observed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ClaimRow(Base):
    __tablename__ = "claims"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    opportunity_id: Mapped[str] = mapped_column(ForeignKey("opportunities.id"))
    category: Mapped[str] = mapped_column(String(20))
    text: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20))
    trust_value: Mapped[float] = mapped_column(Float)
    trust_level: Mapped[str] = mapped_column(String(10))
    trust_rationale: Mapped[str] = mapped_column(Text)
    verification_method: Mapped[str] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class ClaimEvidenceRow(Base):
    __tablename__ = "claim_evidence"
    claim_id: Mapped[str] = mapped_column(ForeignKey("claims.id"), primary_key=True)
    evidence_id: Mapped[str] = mapped_column(ForeignKey("evidence.id"), primary_key=True)
    relation: Mapped[str] = mapped_column(String(20))


class AxisScoreRow(Base):
    __tablename__ = "axis_scores"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    opportunity_id: Mapped[str] = mapped_column(ForeignKey("opportunities.id"))
    thesis_id: Mapped[str] = mapped_column(ForeignKey("theses.id"))
    axis: Mapped[str] = mapped_column(String(20))
    score: Mapped[float] = mapped_column(Float)
    conf_low: Mapped[float] = mapped_column(Float)
    conf_high: Mapped[float] = mapped_column(Float)
    conf_basis: Mapped[str] = mapped_column(Text)
    trend: Mapped[str] = mapped_column(String(30))
    market_stance: Mapped[str | None] = mapped_column(String(10), nullable=True)
    rationale: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class AxisScoreEvidenceRow(Base):
    __tablename__ = "axis_score_evidence"
    axis_score_id: Mapped[str] = mapped_column(ForeignKey("axis_scores.id"), primary_key=True)
    evidence_id: Mapped[str] = mapped_column(ForeignKey("evidence.id"), primary_key=True)


class FounderScoreRow(Base):
    __tablename__ = "founder_scores"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    founder_id: Mapped[str] = mapped_column(ForeignKey("founders.id"))
    score: Mapped[float] = mapped_column(Float)
    conf_low: Mapped[float] = mapped_column(Float)
    conf_high: Mapped[float] = mapped_column(Float)
    inputs: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class MemoRow(Base):
    __tablename__ = "memos"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    opportunity_id: Mapped[str] = mapped_column(ForeignKey("opportunities.id"))
    thesis_id: Mapped[str] = mapped_column(ForeignKey("theses.id"))
    recommendation: Mapped[str] = mapped_column(String(30))
    recommendation_rationale: Mapped[str] = mapped_column(Text, default="")
    sections: Mapped[list] = mapped_column(JSON)
    gaps: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class MemoClaimRow(Base):
    __tablename__ = "memo_claims"
    memo_id: Mapped[str] = mapped_column(ForeignKey("memos.id"), primary_key=True)
    claim_id: Mapped[str] = mapped_column(ForeignKey("claims.id"), primary_key=True)


class TraceRow(Base):
    __tablename__ = "trace_log"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    opportunity_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    module: Mapped[str] = mapped_column(String(60))
    step: Mapped[str] = mapped_column(String(200))
    input_refs: Mapped[list] = mapped_column(JSON, default=list)
    output_refs: Mapped[list] = mapped_column(JSON, default=list)
    model: Mapped[str | None] = mapped_column(String(60), nullable=True)
    summary: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class ContradictionFlagRow(Base):
    __tablename__ = "contradiction_flags"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    claim_id: Mapped[str] = mapped_column(ForeignKey("claims.id"))
    conflicting_evidence_id: Mapped[str] = mapped_column(ForeignKey("evidence.id"))
    note: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
