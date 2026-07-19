"""Repositories: ALL database access lives here. Pipeline modules depend on
these + contracts only — never on SQLAlchemy rows or on each other."""

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.contracts.claims import Claim, ContradictionFlag, EvidenceLink, TrustScore
from app.contracts.entities import CompanyRecord, FounderRecord, Opportunity
from app.contracts.enums import (
    Axis,
    ClaimCategory,
    ClaimStatus,
    PipelineStatus,
    Relation,
    SourceType,
    Stage,
    Stance,
    Track,
    Trend,
    TrustLevel,
)
from app.contracts.enums import Recommendation, SectionKind
from app.contracts.evidence import Evidence
from app.contracts.memo import Memo, MemoSection
from app.contracts.scores import AxisScore, ConfidenceBand, FounderScoreEntry
from app.contracts.thesis import ThesisConfig
from app.contracts.trace import TraceEntry
from app.memory.tables import (
    AxisScoreEvidenceRow,
    AxisScoreRow,
    ClaimEvidenceRow,
    ClaimRow,
    CompanyRow,
    ContradictionFlagRow,
    EvidenceRow,
    FounderCompanyRow,
    FounderRow,
    FounderScoreRow,
    MemoClaimRow,
    MemoRow,
    OpportunityRow,
    ThesisRow,
    TraceRow,
)


def _norm(s: str) -> str:
    return " ".join(s.lower().split())


class ThesisRepository:
    def __init__(self, session: Session):
        self.session = session

    def save(self, config: ThesisConfig, *, make_active: bool = False) -> ThesisConfig:
        row = self.session.get(ThesisRow, str(config.id))
        if row is None:
            row = ThesisRow(id=str(config.id))
            self.session.add(row)
        row.name = config.name
        row.config = config.model_dump(mode="json")
        if make_active:
            for other in self.session.scalars(select(ThesisRow)):
                other.is_active = 0
            row.is_active = 1
        self.session.commit()
        return config

    def get_active(self) -> ThesisConfig | None:
        row = self.session.scalars(select(ThesisRow).where(ThesisRow.is_active == 1)).first()
        return ThesisConfig.model_validate(row.config) if row else None


class FounderRepository:
    def __init__(self, session: Session):
        self.session = session

    def save(self, founder: FounderRecord) -> FounderRecord:
        row = self.session.get(FounderRow, str(founder.id))
        if row is None:
            row = FounderRow(id=str(founder.id), first_seen_at=founder.first_seen_at)
            self.session.add(row)
        row.canonical_name = founder.canonical_name
        row.handles = founder.handles
        row.emails = founder.emails
        row.bio = founder.bio
        self.session.commit()
        return founder

    def get(self, founder_id: UUID) -> FounderRecord | None:
        row = self.session.get(FounderRow, str(founder_id))
        return self._to_contract(row) if row else None

    def find_match(self, *, name: str | None = None, email: str | None = None,
                   handles: dict[str, str] | None = None) -> FounderRecord | None:
        """Exact email/handle match first; normalized-name match second. Nothing fuzzier (R-4)."""
        rows = list(self.session.scalars(select(FounderRow)))
        if email:
            for r in rows:
                if email.lower() in [e.lower() for e in (r.emails or [])]:
                    return self._to_contract(r)
        if handles:
            for r in rows:
                for k, v in handles.items():
                    if (r.handles or {}).get(k, "").lower() == v.lower() and v:
                        return self._to_contract(r)
        if name:
            for r in rows:
                if _norm(r.canonical_name) == _norm(name):
                    return self._to_contract(r)
        return None

    def link_company(self, founder_id: UUID, company_id: UUID, role: str = "founder") -> None:
        existing = self.session.get(FounderCompanyRow, (str(founder_id), str(company_id)))
        if existing is None:
            self.session.add(FounderCompanyRow(
                founder_id=str(founder_id), company_id=str(company_id), role=role))
            self.session.commit()

    @staticmethod
    def _to_contract(row: FounderRow) -> FounderRecord:
        return FounderRecord(
            id=UUID(row.id), canonical_name=row.canonical_name,
            handles=row.handles or {}, emails=row.emails or [],
            bio=row.bio, first_seen_at=row.first_seen_at)


class CompanyRepository:
    def __init__(self, session: Session):
        self.session = session

    def save(self, company: CompanyRecord) -> CompanyRecord:
        row = self.session.get(CompanyRow, str(company.id))
        if row is None:
            row = CompanyRow(id=str(company.id))
            self.session.add(row)
        row.name = company.name
        row.sector = company.sector
        row.geography = company.geography
        row.stage = company.stage.value if company.stage else None
        row.one_liner = company.one_liner
        self.session.commit()
        return company

    def get(self, company_id: UUID) -> CompanyRecord | None:
        row = self.session.get(CompanyRow, str(company_id))
        return self._to_contract(row, self.session) if row else None

    def find_by_name(self, name: str) -> CompanyRecord | None:
        for row in self.session.scalars(select(CompanyRow)):
            if _norm(row.name) == _norm(name):
                return self._to_contract(row, self.session)
        return None

    @staticmethod
    def _to_contract(row: CompanyRow, session: Session) -> CompanyRecord:
        founder_ids = [
            UUID(fc.founder_id)
            for fc in session.scalars(
                select(FounderCompanyRow).where(FounderCompanyRow.company_id == row.id))
        ]
        return CompanyRecord(
            id=UUID(row.id), name=row.name, founder_ids=founder_ids,
            sector=row.sector, geography=row.geography,
            stage=Stage(row.stage) if row.stage else None, one_liner=row.one_liner)


class OpportunityRepository:
    def __init__(self, session: Session):
        self.session = session

    def save(self, opp: Opportunity) -> Opportunity:
        row = self.session.get(OpportunityRow, str(opp.id))
        if row is None:
            row = OpportunityRow(id=str(opp.id), created_at=opp.created_at)
            self.session.add(row)
        row.company_id = str(opp.company_id)
        row.track = opp.track.value
        row.status = opp.status.value
        self.session.commit()
        return opp

    def get(self, opp_id: UUID) -> Opportunity | None:
        row = self.session.get(OpportunityRow, str(opp_id))
        return self._to_contract(row) if row else None

    def list_all(self) -> list[Opportunity]:
        rows = self.session.scalars(
            select(OpportunityRow).order_by(OpportunityRow.created_at.desc()))
        return [self._to_contract(r) for r in rows]

    def set_status(self, opp_id: UUID, status: PipelineStatus) -> None:
        row = self.session.get(OpportunityRow, str(opp_id))
        if row:
            row.status = status.value
            self.session.commit()

    @staticmethod
    def _to_contract(row: OpportunityRow) -> Opportunity:
        return Opportunity(
            id=UUID(row.id), company_id=UUID(row.company_id),
            track=Track(row.track), status=PipelineStatus(row.status),
            created_at=row.created_at)


class EvidenceRepository:
    def __init__(self, session: Session):
        self.session = session

    def save(self, ev: Evidence) -> Evidence:
        row = EvidenceRow(
            id=str(ev.id),
            founder_id=str(ev.founder_id) if ev.founder_id else None,
            opportunity_id=str(ev.opportunity_id) if ev.opportunity_id else None,
            source_type=ev.source_type.value, source_ref=ev.source_ref,
            content=ev.content, content_hash=ev.content_hash,
            retrieved_at=ev.retrieved_at, observed_at=ev.observed_at)
        self.session.add(row)
        self.session.commit()
        return ev

    def get(self, evidence_id: UUID) -> Evidence | None:
        row = self.session.get(EvidenceRow, str(evidence_id))
        return self._to_contract(row) if row else None

    def exists_hash(self, content_hash: str) -> bool:
        return self.session.scalar(
            select(func.count()).select_from(EvidenceRow)
            .where(EvidenceRow.content_hash == content_hash)) > 0

    def for_opportunity(self, opp_id: UUID) -> list[Evidence]:
        rows = self.session.scalars(
            select(EvidenceRow).where(EvidenceRow.opportunity_id == str(opp_id)))
        return [self._to_contract(r) for r in rows]

    def for_founder(self, founder_id: UUID) -> list[Evidence]:
        rows = self.session.scalars(
            select(EvidenceRow).where(EvidenceRow.founder_id == str(founder_id)))
        return [self._to_contract(r) for r in rows]

    def search_text(self, query: str, k: int = 8) -> list[Evidence]:
        rows = self.session.scalars(
            select(EvidenceRow).where(EvidenceRow.content.like(f"%{query}%")).limit(k))
        return [self._to_contract(r) for r in rows]

    def count(self) -> int:
        return self.session.scalar(select(func.count()).select_from(EvidenceRow))

    @staticmethod
    def _to_contract(row: EvidenceRow) -> Evidence:
        return Evidence(
            id=UUID(row.id),
            founder_id=UUID(row.founder_id) if row.founder_id else None,
            opportunity_id=UUID(row.opportunity_id) if row.opportunity_id else None,
            source_type=SourceType(row.source_type), source_ref=row.source_ref,
            content=row.content, content_hash=row.content_hash,
            retrieved_at=row.retrieved_at, observed_at=row.observed_at)


class ClaimRepository:
    def __init__(self, session: Session):
        self.session = session

    def save(self, claim: Claim) -> Claim:
        row = self.session.get(ClaimRow, str(claim.id))
        if row is None:
            row = ClaimRow(id=str(claim.id), created_at=claim.created_at)
            self.session.add(row)
        row.opportunity_id = str(claim.opportunity_id)
        row.category = claim.category.value
        row.text = claim.text
        row.status = claim.status.value
        row.trust_value = claim.trust.value
        row.trust_level = claim.trust.level.value
        row.trust_rationale = claim.trust.rationale
        row.verification_method = claim.trust.verification_method
        for link in claim.evidence_links:
            existing = self.session.get(ClaimEvidenceRow, (str(claim.id), str(link.evidence_id)))
            if existing is None:
                self.session.add(ClaimEvidenceRow(
                    claim_id=str(claim.id), evidence_id=str(link.evidence_id),
                    relation=link.relation.value))
            else:
                existing.relation = link.relation.value
        self.session.commit()
        return claim

    def for_opportunity(self, opp_id: UUID) -> list[Claim]:
        rows = self.session.scalars(
            select(ClaimRow).where(ClaimRow.opportunity_id == str(opp_id)))
        return [self._to_contract(r) for r in rows]

    def save_flag(self, flag: ContradictionFlag) -> ContradictionFlag:
        self.session.add(ContradictionFlagRow(
            id=str(flag.id), claim_id=str(flag.claim_id),
            conflicting_evidence_id=str(flag.conflicting_evidence_id),
            note=flag.note, created_at=flag.created_at))
        self.session.commit()
        return flag

    def _to_contract(self, row: ClaimRow) -> Claim:
        links = [
            EvidenceLink(evidence_id=UUID(le.evidence_id), relation=Relation(le.relation))
            for le in self.session.scalars(
                select(ClaimEvidenceRow).where(ClaimEvidenceRow.claim_id == row.id))
        ]
        return Claim(
            id=UUID(row.id), opportunity_id=UUID(row.opportunity_id),
            category=ClaimCategory(row.category), text=row.text,
            status=ClaimStatus(row.status),
            trust=TrustScore(
                value=row.trust_value, level=TrustLevel(row.trust_level),
                rationale=row.trust_rationale, verification_method=row.verification_method),
            evidence_links=links, created_at=row.created_at)


class AxisScoreRepository:
    """Append-only by design: every save is a new row, so trends are queryable."""

    def __init__(self, session: Session):
        self.session = session

    def save(self, score: AxisScore) -> AxisScore:
        self.session.add(AxisScoreRow(
            id=str(score.id), opportunity_id=str(score.opportunity_id),
            thesis_id=str(score.thesis_id), axis=score.axis.value, score=score.score,
            conf_low=score.confidence.low, conf_high=score.confidence.high,
            conf_basis=score.confidence.basis, trend=score.trend.value,
            market_stance=score.market_stance.value if score.market_stance else None,
            rationale=score.rationale, created_at=score.created_at))
        for ev_id in score.evidence_ids:
            self.session.add(AxisScoreEvidenceRow(
                axis_score_id=str(score.id), evidence_id=str(ev_id)))
        self.session.commit()
        return score

    def history(self, opp_id: UUID, axis: Axis) -> list[AxisScore]:
        rows = self.session.scalars(
            select(AxisScoreRow)
            .where(AxisScoreRow.opportunity_id == str(opp_id), AxisScoreRow.axis == axis.value)
            .order_by(AxisScoreRow.created_at))
        return [self._to_contract(r) for r in rows]

    def latest_all(self, opp_id: UUID) -> dict[Axis, AxisScore]:
        out: dict[Axis, AxisScore] = {}
        for axis in Axis:
            hist = self.history(opp_id, axis)
            if hist:
                out[axis] = hist[-1]
        return out

    def _to_contract(self, row: AxisScoreRow) -> AxisScore:
        ev_ids = [
            UUID(link.evidence_id)
            for link in self.session.scalars(
                select(AxisScoreEvidenceRow)
                .where(AxisScoreEvidenceRow.axis_score_id == row.id))
        ]
        return AxisScore(
            id=UUID(row.id), opportunity_id=UUID(row.opportunity_id),
            thesis_id=UUID(row.thesis_id), axis=Axis(row.axis), score=row.score,
            confidence=ConfidenceBand(low=row.conf_low, high=row.conf_high, basis=row.conf_basis),
            trend=Trend(row.trend),
            market_stance=Stance(row.market_stance) if row.market_stance else None,
            rationale=row.rationale, evidence_ids=ev_ids, created_at=row.created_at)


class FounderScoreRepository:
    """The Founder Score: append-only, keyed by PERSON. Persists across
    applications, never resets (brief FAQ 6)."""

    def __init__(self, session: Session):
        self.session = session

    def save(self, entry: FounderScoreEntry) -> FounderScoreEntry:
        self.session.add(FounderScoreRow(
            id=str(entry.id), founder_id=str(entry.founder_id), score=entry.score,
            conf_low=entry.confidence.low, conf_high=entry.confidence.high,
            inputs={**entry.inputs, "conf_basis": entry.confidence.basis},
            created_at=entry.created_at))
        self.session.commit()
        return entry

    def history(self, founder_id: UUID) -> list[FounderScoreEntry]:
        rows = self.session.scalars(
            select(FounderScoreRow)
            .where(FounderScoreRow.founder_id == str(founder_id))
            .order_by(FounderScoreRow.created_at))
        return [self._to_contract(r) for r in rows]

    def latest(self, founder_id: UUID) -> FounderScoreEntry | None:
        history = self.history(founder_id)
        return history[-1] if history else None

    @staticmethod
    def _to_contract(row: FounderScoreRow) -> FounderScoreEntry:
        inputs = dict(row.inputs or {})
        basis = inputs.pop("conf_basis", "heuristic")
        return FounderScoreEntry(
            id=UUID(row.id), founder_id=UUID(row.founder_id), score=row.score,
            confidence=ConfidenceBand(low=row.conf_low, high=row.conf_high, basis=basis),
            inputs=inputs, created_at=row.created_at)


class MemoRepository:
    def __init__(self, session: Session):
        self.session = session

    def save(self, memo: Memo) -> Memo:
        self.session.add(MemoRow(
            id=str(memo.id), opportunity_id=str(memo.opportunity_id),
            thesis_id=str(memo.thesis_id), recommendation=memo.recommendation.value,
            recommendation_rationale=memo.recommendation_rationale,
            sections=[s.model_dump(mode="json") for s in memo.sections],
            gaps=memo.gaps, created_at=memo.created_at))
        for claim_id in memo.claim_ids:
            self.session.add(MemoClaimRow(memo_id=str(memo.id), claim_id=str(claim_id)))
        self.session.commit()
        return memo

    def latest(self, opp_id: UUID) -> Memo | None:
        row = self.session.scalars(
            select(MemoRow).where(MemoRow.opportunity_id == str(opp_id))
            .order_by(MemoRow.created_at.desc())).first()
        if row is None:
            return None
        claim_ids = [
            UUID(mc.claim_id)
            for mc in self.session.scalars(
                select(MemoClaimRow).where(MemoClaimRow.memo_id == row.id))
        ]
        return Memo(
            id=UUID(row.id), opportunity_id=UUID(row.opportunity_id),
            thesis_id=UUID(row.thesis_id),
            recommendation=Recommendation(row.recommendation),
            recommendation_rationale=row.recommendation_rationale or "",
            sections=[MemoSection(kind=SectionKind(s["kind"]), markdown=s["markdown"])
                      for s in (row.sections or [])],
            claim_ids=claim_ids, gaps=row.gaps or [], created_at=row.created_at)


class TraceRepository:
    def __init__(self, session: Session):
        self.session = session

    def save(self, entry: TraceEntry) -> TraceEntry:
        self.session.add(TraceRow(
            id=str(entry.id),
            opportunity_id=str(entry.opportunity_id) if entry.opportunity_id else None,
            module=entry.module, step=entry.step,
            input_refs=[str(r) for r in entry.input_refs],
            output_refs=[str(r) for r in entry.output_refs],
            model=entry.model, summary=entry.summary, created_at=entry.created_at))
        self.session.commit()
        return entry

    def for_opportunity(self, opp_id: UUID) -> list[TraceEntry]:
        rows = self.session.scalars(
            select(TraceRow).where(TraceRow.opportunity_id == str(opp_id))
            .order_by(TraceRow.created_at))
        return [
            TraceEntry(
                id=UUID(r.id), opportunity_id=UUID(r.opportunity_id) if r.opportunity_id else None,
                module=r.module, step=r.step,
                input_refs=[UUID(x) for x in (r.input_refs or [])],
                output_refs=[UUID(x) for x in (r.output_refs or [])],
                model=r.model, summary=r.summary, created_at=r.created_at)
            for r in rows
        ]
