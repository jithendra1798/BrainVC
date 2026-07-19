"""Orchestrator: plain sequential pipeline (DECISIONS D-2 — no agent framework).

extract → gate → score (pre-diligence) → validate → score (post-diligence,
so bands narrow honestly and trend becomes visible) → memo.

Also instruments stage timings — 'how fast an opportunity moves from first
signal to decision' is an explicit evaluation criterion.
"""

import time
from uuid import UUID

from sqlalchemy.orm import Session

from app.contracts.enums import PipelineStatus
from app.extraction.extractor import ClaimExtractor
from app.memo.composer import MemoComposer
from app.memory.repositories import (
    AxisScoreRepository,
    ClaimRepository,
    CompanyRepository,
    EvidenceRepository,
    FounderRepository,
    FounderScoreRepository,
    MemoRepository,
    OpportunityRepository,
    ThesisRepository,
    TraceRepository,
)
from app.screening.gate import ViabilityGate
from app.scoring.axes.scorers import score_all_axes
from app.scoring.cold_start.scorer import rebuild_assessment
from app.thesis.provider import ThesisProvider
from app.trace.logger import TraceLogger
from app.validation.validator import Validator


def run_full(session: Session, opportunity_id: UUID) -> dict:
    opp_repo = OpportunityRepository(session)
    opp = opp_repo.get(opportunity_id)
    if opp is None:
        raise ValueError("opportunity not found")

    claim_repo = ClaimRepository(session)
    evidence_repo = EvidenceRepository(session)
    score_repo = AxisScoreRepository(session)
    trace = TraceLogger(TraceRepository(session))
    thesis = ThesisProvider(ThesisRepository(session)).get_active()

    timeline: list[dict] = []
    started = time.perf_counter()

    def mark(stage: str, summary: str):
        timeline.append({
            "stage": stage,
            "elapsed_s": round(time.perf_counter() - started, 1),
            "summary": summary,
        })

    evidence = evidence_repo.for_opportunity(opp.id)

    # Memory feeding scoring: if this founder has a persisted Founder Score
    # (e.g. from an earlier outbound scan or prior application), the founder
    # axis consumes it — the score follows the PERSON, never resets.
    cold_start = None
    company = CompanyRepository(session).get(opp.company_id)
    if company and company.founder_ids:
        latest_entry = FounderScoreRepository(session).latest(company.founder_ids[0])
        if latest_entry is not None:
            cold_start = rebuild_assessment(latest_entry)

    claims = claim_repo.for_opportunity(opp.id)
    if not claims:
        claims = ClaimExtractor(claim_repo, trace).extract(opp.id, evidence)
    mark("extract", f"{len(claims)} claims")

    gate = ViabilityGate(trace).screen(opp.id, thesis, evidence)
    if not gate.viable:
        opp_repo.set_status(opp.id, PipelineStatus.REJECTED_AT_GATE)
        mark("gate", f"REJECTED: {gate.reason}")
        return {"status": PipelineStatus.REJECTED_AT_GATE, "timeline": timeline}
    mark("gate", "viable")

    score_all_axes(opp.id, thesis, claims, evidence, score_repo, trace,
                   cold_start=cold_start)
    opp_repo.set_status(opp.id, PipelineStatus.SCREENED)
    mark("score_pre", "3 axes scored (pre-diligence)"
         + (" — founder axis informed by persisted Founder Score" if cold_start else ""))

    claims = Validator(claim_repo, evidence_repo, trace).validate(opp.id, claims, evidence)
    opp_repo.set_status(opp.id, PipelineStatus.IN_DILIGENCE)
    contradicted = sum(1 for c in claims if c.status == "contradicted")
    mark("validate", f"{len(claims)} claims validated, {contradicted} contradicted")

    evidence = evidence_repo.for_opportunity(opp.id)  # may now include WEB evidence
    scores = score_all_axes(opp.id, thesis, claims, evidence, score_repo, trace,
                            cold_start=cold_start)
    mark("score_post", "3 axes re-scored post-diligence (bands + trend updated)")

    founder = None
    if company and company.founder_ids:
        founder = FounderRepository(session).get(company.founder_ids[0])
    memo = MemoComposer(MemoRepository(session), trace).compose(
        opp.id, thesis, company, founder, scores, claims)
    opp_repo.set_status(opp.id, PipelineStatus.DECIDED)
    mark("memo", f"recommendation={memo.recommendation.value}")

    return {
        "status": PipelineStatus.DECIDED,
        "recommendation": memo.recommendation.value,
        "memo_id": str(memo.id),
        "timeline": timeline,
        "total_seconds": round(time.perf_counter() - started, 1),
    }
