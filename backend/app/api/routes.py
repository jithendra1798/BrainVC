from pathlib import Path
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.api.deps import get_session
from app.contracts.entities import Opportunity
from app.contracts.enums import PipelineStatus, Track
from app.contracts.signals import ConnectorQuery
from app.contracts.thesis import ThesisConfig
from app.extraction.extractor import ClaimExtractor
from app.ingestion.entity_resolution import EntityResolver
from app.ingestion.ingestor import Ingestor
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
from app.scoring.cold_start.scorer import ColdStartScorer
from app.pipeline.orchestrator import run_full
from app.screening.gate import ViabilityGate
from app.scoring.axes.scorers import score_all_axes
from app.validation.validator import Validator
from app.sourcing.registry import get_connector
from app.thesis.provider import ThesisProvider
from app.trace.logger import TraceLogger

router = APIRouter()

UPLOAD_DIR = Path(__file__).resolve().parents[2] / "data" / "uploads"


@router.get("/health")
def health():
    return {"status": "ok"}


@router.get("/thesis", response_model=ThesisConfig)
def get_thesis(session: Session = Depends(get_session)):
    return ThesisProvider(ThesisRepository(session)).get_active()


@router.put("/thesis", response_model=ThesisConfig)
def set_thesis(config: ThesisConfig, session: Session = Depends(get_session)):
    return ThesisProvider(ThesisRepository(session)).set_active(config)


@router.post("/apply")
async def apply(
    company_name: str = Form(...),
    founder_name: str = Form(...),
    founder_email: str | None = Form(None),
    one_liner: str | None = Form(None),
    deck: UploadFile = File(...),
    session: Session = Depends(get_session),
):
    """Inbound track: deck + company name is the minimum bar (per brief)."""
    trace = TraceLogger(TraceRepository(session))
    resolver = EntityResolver(FounderRepository(session), CompanyRepository(session))

    founder = resolver.resolve_or_create_founder(name=founder_name, email=founder_email)
    company = resolver.resolve_or_create_company(name=company_name, one_liner=one_liner)
    FounderRepository(session).link_company(founder.id, company.id)

    opportunity = OpportunityRepository(session).save(
        Opportunity(company_id=company.id, track=Track.INBOUND))

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    suffix = Path(deck.filename or "deck.md").suffix or ".md"
    deck_path = UPLOAD_DIR / f"{uuid4().hex}{suffix}"
    deck_path.write_bytes(await deck.read())

    trace.log(module="sourcing.inbound_deck", step="application_received",
              opportunity_id=opportunity.id,
              summary=f"Inbound application: {company_name} / {founder_name}, "
                      f"deck={deck.filename}")

    signals = get_connector("inbound_deck").fetch(ConnectorQuery(params={
        "path": str(deck_path), "founder": founder_name, "company": company_name}))

    result = Ingestor(EvidenceRepository(session), trace).ingest(
        signals, opportunity_id=opportunity.id, founder_id=founder.id)

    return {
        "opportunity_id": str(opportunity.id),
        "company_id": str(company.id),
        "founder_id": str(founder.id),
        "slides_parsed": len(signals),
        "evidence_created": len(result.created),
        "evidence_deduplicated": result.deduped,
    }


@router.get("/opportunities")
def list_opportunities(session: Session = Depends(get_session)):
    opp_repo = OpportunityRepository(session)
    company_repo = CompanyRepository(session)
    evidence_repo = EvidenceRepository(session)
    out = []
    for opp in opp_repo.list_all():
        company = company_repo.get(opp.company_id)
        out.append({
            "id": str(opp.id),
            "company_name": company.name if company else "?",
            "track": opp.track,
            "status": opp.status,
            "created_at": opp.created_at.isoformat(),
            "evidence_count": len(evidence_repo.for_opportunity(opp.id)),
        })
    return out


@router.get("/opportunities/{opp_id}")
def get_opportunity(opp_id: UUID, session: Session = Depends(get_session)):
    opp = OpportunityRepository(session).get(opp_id)
    if opp is None:
        raise HTTPException(404, "opportunity not found")
    company = CompanyRepository(session).get(opp.company_id)
    evidence = EvidenceRepository(session).for_opportunity(opp.id)
    return {
        "opportunity": opp.model_dump(mode="json"),
        "company": company.model_dump(mode="json") if company else None,
        "evidence": [e.model_dump(mode="json") for e in evidence],
    }


@router.post("/opportunities/{opp_id}/extract")
def extract_claims(opp_id: UUID, session: Session = Depends(get_session)):
    opp = OpportunityRepository(session).get(opp_id)
    if opp is None:
        raise HTTPException(404, "opportunity not found")
    evidence = EvidenceRepository(session).for_opportunity(opp.id)
    if not evidence:
        raise HTTPException(400, "no evidence to extract from")
    extractor = ClaimExtractor(ClaimRepository(session), TraceLogger(TraceRepository(session)))
    claims = extractor.extract(opp.id, evidence)
    return {"claims_extracted": len(claims),
            "claims": [c.model_dump(mode="json") for c in claims]}


@router.post("/opportunities/{opp_id}/screen")
def screen(opp_id: UUID, session: Session = Depends(get_session)):
    """Viability gate, then 3 independent axis scores (never averaged)."""
    opp_repo = OpportunityRepository(session)
    opp = opp_repo.get(opp_id)
    if opp is None:
        raise HTTPException(404, "opportunity not found")
    claims = ClaimRepository(session).for_opportunity(opp.id)
    if not claims:
        raise HTTPException(400, "no claims — run /extract first")
    evidence = EvidenceRepository(session).for_opportunity(opp.id)
    thesis = ThesisProvider(ThesisRepository(session)).get_active()
    trace = TraceLogger(TraceRepository(session))

    gate = ViabilityGate(trace).screen(opp.id, thesis, evidence)
    if not gate.viable:
        opp_repo.set_status(opp.id, PipelineStatus.REJECTED_AT_GATE)
        return {"gate": gate.model_dump(), "scores": []}

    scores = score_all_axes(
        opp.id, thesis, claims, evidence, AxisScoreRepository(session), trace)
    opp_repo.set_status(opp.id, PipelineStatus.SCREENED)
    return {"gate": gate.model_dump(),
            "scores": [s.model_dump(mode="json") for s in scores]}


@router.post("/opportunities/{opp_id}/validate")
def validate(opp_id: UUID, session: Session = Depends(get_session)):
    """Adversarial validator: per-claim trust scores + contradiction flags."""
    opp_repo = OpportunityRepository(session)
    opp = opp_repo.get(opp_id)
    if opp is None:
        raise HTTPException(404, "opportunity not found")
    claims = ClaimRepository(session).for_opportunity(opp.id)
    if not claims:
        raise HTTPException(400, "no claims — run /extract first")
    evidence = EvidenceRepository(session).for_opportunity(opp.id)
    validator = Validator(ClaimRepository(session), EvidenceRepository(session),
                          TraceLogger(TraceRepository(session)))
    updated = validator.validate(opp.id, claims, evidence)
    opp_repo.set_status(opp.id, PipelineStatus.IN_DILIGENCE)
    return {
        "claims_validated": len(updated),
        "contradicted": sum(1 for c in updated if c.status == "contradicted"),
        "claims": [c.model_dump(mode="json") for c in updated],
    }


@router.get("/opportunities/{opp_id}/scores")
def get_scores(opp_id: UUID, session: Session = Depends(get_session)):
    latest = AxisScoreRepository(session).latest_all(opp_id)
    return {axis.value: score.model_dump(mode="json") for axis, score in latest.items()}


@router.get("/opportunities/{opp_id}/claims")
def get_claims(opp_id: UUID, session: Session = Depends(get_session)):
    claims = ClaimRepository(session).for_opportunity(opp_id)
    return [c.model_dump(mode="json") for c in claims]


@router.post("/opportunities/{opp_id}/memo")
def compose_memo(opp_id: UUID, session: Session = Depends(get_session)):
    opp_repo = OpportunityRepository(session)
    opp = opp_repo.get(opp_id)
    if opp is None:
        raise HTTPException(404, "opportunity not found")
    claims = ClaimRepository(session).for_opportunity(opp.id)
    scores = list(AxisScoreRepository(session).latest_all(opp.id).values())
    if not claims or not scores:
        raise HTTPException(400, "run /extract and /screen first")
    thesis = ThesisProvider(ThesisRepository(session)).get_active()
    company = CompanyRepository(session).get(opp.company_id)
    founder = None
    if company and company.founder_ids:
        founder = FounderRepository(session).get(company.founder_ids[0])
    memo = MemoComposer(MemoRepository(session), TraceLogger(TraceRepository(session))).compose(
        opp.id, thesis, company, founder, scores, claims)
    opp_repo.set_status(opp.id, PipelineStatus.DECIDED)
    return memo.model_dump(mode="json")


@router.get("/opportunities/{opp_id}/memo")
def get_memo(opp_id: UUID, session: Session = Depends(get_session)):
    memo = MemoRepository(session).latest(opp_id)
    if memo is None:
        raise HTTPException(404, "no memo yet")
    claims = {str(c.id): c.model_dump(mode="json")
              for c in ClaimRepository(session).for_opportunity(opp_id)}
    return {"memo": memo.model_dump(mode="json"), "claims": claims}


@router.get("/opportunities/{opp_id}/brief.mp3")
def voice_brief(opp_id: UUID, session: Session = Depends(get_session)):
    """Voice briefing of the memo (ElevenLabs). Generated on demand, cached."""
    from fastapi import Response

    from app.memo import voice

    if not voice.is_enabled():
        raise HTTPException(503, "ELEVENLABS_API_KEY not set")
    path = voice.brief_path(str(opp_id))
    if not path.exists():
        memo = MemoRepository(session).latest(opp_id)
        if memo is None:
            raise HTTPException(404, "no memo yet — run the pipeline first")
        opp = OpportunityRepository(session).get(opp_id)
        company = CompanyRepository(session).get(opp.company_id) if opp else None
        claims = ClaimRepository(session).for_opportunity(opp_id)
        text = voice.briefing_text(company.name if company else "the company", memo, claims)
        path.write_bytes(voice.synthesize(text))
        TraceLogger(TraceRepository(session)).log(
            module="memo.voice", step="voice_brief", opportunity_id=opp_id,
            summary=f"Voice briefing generated ({len(text)} chars)")
    return Response(content=path.read_bytes(), media_type="audio/mpeg")


@router.post("/opportunities/{opp_id}/run")
def run_pipeline(opp_id: UUID, session: Session = Depends(get_session)):
    """Full pipeline: extract → gate → score → validate → re-score → memo."""
    try:
        return run_full(session, opp_id)
    except ValueError as err:
        raise HTTPException(404, str(err)) from err


@router.get("/pipeline/ranked")
def ranked_pipeline(session: Session = Depends(get_session)):
    """Ranked list under the active thesis. Axes are NEVER merged for display;
    ordering_key is thesis-weighted and labeled as ordering-only."""
    thesis = ThesisProvider(ThesisRepository(session)).get_active()
    weights = thesis.axis_weights
    score_repo = AxisScoreRepository(session)
    memo_repo = MemoRepository(session)
    company_repo = CompanyRepository(session)

    rows = []
    for opp in OpportunityRepository(session).list_all():
        latest = score_repo.latest_all(opp.id)
        company = company_repo.get(opp.company_id)
        memo = memo_repo.latest(opp.id)
        axes = {axis.value: {
            "score": s.score,
            "band": [s.confidence.low, s.confidence.high],
            "trend": s.trend,
            "stance": s.market_stance,
        } for axis, s in latest.items()}
        if latest:
            weight_map = {"founder": weights.founder, "market": weights.market,
                          "idea_vs_market": weights.idea_vs_market}
            total_weight = sum(weight_map[a.value] for a in latest)
            ordering_key = round(sum(
                s.score * weight_map[axis.value] for axis, s in latest.items()
            ) / total_weight, 1)
        else:
            ordering_key = None
        rows.append({
            "opportunity_id": str(opp.id),
            "company_name": company.name if company else "?",
            "track": opp.track,
            "status": opp.status,
            "axes": axes,
            "ordering_key": ordering_key,  # thesis-weighted, ordering ONLY
            "recommendation": memo.recommendation if memo else None,
        })
    rows.sort(key=lambda r: (r["status"] == "rejected_at_gate",
                             -(r["ordering_key"] or -1)))
    return {"thesis": thesis.name, "opportunities": rows}


@router.post("/outbound/scan")
def outbound_scan(payload: dict, session: Session = Depends(get_session)):
    """Outbound track: scan a public GitHub footprint → founder + evidence +
    cold-start Founder Score. No opportunity yet — that's born at activation."""
    handle = payload.get("github_handle", "").strip().lstrip("@")
    if not handle:
        raise HTTPException(400, "github_handle required")
    trace = TraceLogger(TraceRepository(session))

    signals = get_connector("github").fetch(ConnectorQuery(params={"handle": handle}))
    display_name = payload.get("founder_name") or signals[0].founder_hint or handle
    founder = EntityResolver(
        FounderRepository(session), CompanyRepository(session)
    ).resolve_or_create_founder(name=display_name, handles={"github": handle})

    trace.log(module="sourcing.github", step="outbound_scan",
              summary=f"Scanned @{handle}: {len(signals)} signals "
                      f"→ founder {founder.canonical_name}")
    result = Ingestor(EvidenceRepository(session), trace).ingest(
        signals, founder_id=founder.id)

    evidence = EvidenceRepository(session).for_founder(founder.id)
    assessment = ColdStartScorer(FounderScoreRepository(session), trace).assess(
        founder, evidence)

    return {
        "founder_id": str(founder.id),
        "founder_name": founder.canonical_name,
        "signals": len(signals),
        "evidence_created": len(result.created),
        "evidence_deduplicated": result.deduped,
        "cold_start": assessment.model_dump(mode="json"),
    }


@router.get("/founders")
def list_founders(session: Session = Depends(get_session)):
    founder_repo = FounderRepository(session)
    score_repo = FounderScoreRepository(session)
    evidence_repo = EvidenceRepository(session)
    from sqlalchemy import select as _select

    from app.memory.tables import FounderRow
    out = []
    for row in session.scalars(_select(FounderRow)):
        founder = founder_repo.get(UUID(row.id))
        history = score_repo.history(founder.id)
        out.append({
            "id": str(founder.id),
            "name": founder.canonical_name,
            "handles": founder.handles,
            "evidence_count": len(evidence_repo.for_founder(founder.id)),
            "founder_score": history[-1].score if history else None,
            "score_history": [
                {"score": e.score, "low": e.confidence.low, "high": e.confidence.high,
                 "at": e.created_at.isoformat()} for e in history],
        })
    out.sort(key=lambda f: -(f["founder_score"] or -1))
    return out


@router.get("/founders/{founder_id}")
def founder_detail(founder_id: UUID, session: Session = Depends(get_session)):
    founder = FounderRepository(session).get(founder_id)
    if founder is None:
        raise HTTPException(404, "founder not found")
    history = FounderScoreRepository(session).history(founder.id)
    return {
        "founder": founder.model_dump(mode="json"),
        "evidence": [e.model_dump(mode="json")
                     for e in EvidenceRepository(session).for_founder(founder.id)],
        "score_history": [e.model_dump(mode="json") for e in history],
    }


@router.post("/outbound/activate/{founder_id}")
def activate(founder_id: UUID, session: Session = Depends(get_session)):
    """Activate: draft real outreach (cold outreach, not cold investment —
    the goal is to trigger an application into the same inbound funnel)."""
    founder = FounderRepository(session).get(founder_id)
    if founder is None:
        raise HTTPException(404, "founder not found")
    latest = FounderScoreRepository(session).latest(founder.id)
    if latest is None:
        raise HTTPException(400, "run /outbound/scan first")
    evidence = EvidenceRepository(session).for_founder(founder.id)

    from pydantic import BaseModel as _BaseModel

    from app.llm.client import parse_structured

    class OutreachDraft(_BaseModel):
        subject: str
        body: str

    excerpts = "\n".join(f"- {e.content[:160]}" for e in evidence[:6])
    draft = parse_structured(
        role="gate",
        system="You draft short, specific founder outreach for a pre-seed fund. "
               "Reference the person's ACTUAL public work (repos, projects) — no "
               "flattery boilerplate. Goal: invite them to apply for a $100K "
               "check decided within 24 hours. 4 sentences max.",
        user=f"Founder: {founder.canonical_name} (handles: {founder.handles})\n"
             f"Footprint highlights:\n{excerpts}",
        schema=OutreachDraft)
    TraceLogger(TraceRepository(session)).log(
        module="sourcing.activate", step="outreach_draft",
        summary=f"Outreach drafted for {founder.canonical_name}")
    return {"founder_id": str(founder_id), "draft": draft.model_dump()}


@router.get("/opportunities/{opp_id}/trace")
def get_trace(opp_id: UUID, session: Session = Depends(get_session)):
    entries = TraceRepository(session).for_opportunity(opp_id)
    return [e.model_dump(mode="json") for e in entries]
