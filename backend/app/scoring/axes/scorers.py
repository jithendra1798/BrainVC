"""Three INDEPENDENT axis scorers (brief §6: never averaged).

Each axis: its own prompt, its own LLM call, its own persisted score with
trend + confidence band + cited evidence. The thesis config is injected into
every prompt — the same founder scores differently under a different thesis.

Cold-start plug-in point: FounderAxisScorer accepts an optional
ColdStartAssessment (stage 6) which is appended to its prompt context.
"""

from uuid import UUID

from pydantic import BaseModel

from app.contracts.claims import Claim
from app.contracts.enums import Axis, Stance, Trend
from app.contracts.evidence import Evidence
from app.contracts.scores import AxisScore, ColdStartAssessment
from app.contracts.thesis import ThesisConfig
from app.llm.client import parse_structured
from app.llm.config import MODELS
from app.memory.repositories import AxisScoreRepository
from app.scoring.calibration.heuristic import compute_band
from app.trace.logger import TraceLogger


class AxisOutput(BaseModel):
    score: float  # 0–100
    rationale: str  # 2–4 sentences, must reference evidence indices like [3]
    key_evidence_indices: list[int]
    stance: Stance | None  # market axis only; null elsewhere


AXIS_PROMPTS: dict[Axis, str] = {
    Axis.FOUNDER: """Score the FOUNDER axis (0-100): who this person is — traits,
capability, and track record as evidenced. Judge execution signals (shipped work,
prior roles, public artifacts), not the market or the idea. Under a
'back_potential_over_traction' risk posture, weight capability signals over
current revenue. Claims carry status + trust from the adversarial validator:
weight supported claims fully, discount unverifiable ones, and treat
contradicted/flagged claims as active red flags.

ABSENCE OF PUBLIC FOOTPRINT IS NOT A NEGATIVE SIGNAL. Our own backtest
(RESEARCH.md) found elite public footprint fails to predict founding even when
present (AUC 0.20, blinded & time-sliced). When founder evidence is thin:
anchor near the middle (45-60), name exactly what is unobservable in the
rationale, and let the confidence band — not a punitive score — carry the
uncertainty. Punishing invisibility rebuilds the network-gated system this
fund exists to replace. Set stance to null.""",
    Axis.MARKET: """Score the MARKET axis (0-100): market sizing, competitive
landscape, and structural urgency — independent of who the founder is. Also set
stance: bullish, neutral, or bear on this market for the fund's thesis. Include a
brief SWOT flavor in the rationale (strongest pro, strongest risk).""",
    Axis.IDEA_VS_MARKET: """Score the IDEA-VS-MARKET axis (0-100): does the idea
as pitched survive scrutiny in this market — and if not, is the team strong
enough to pivot? High score = idea fits market as-is OR clear pivot capacity.
Set stance to null.""",
}


class AxisScorer:
    def __init__(self, axis: Axis, score_repo: AxisScoreRepository, trace: TraceLogger):
        self.axis = axis
        self.score_repo = score_repo
        self.trace = trace

    def score(self, opportunity_id: UUID, thesis: ThesisConfig, claims: list[Claim],
              evidence: list[Evidence],
              cold_start: ColdStartAssessment | None = None) -> AxisScore:
        numbered_evidence = "\n\n".join(
            f"[{i}] (source: {ev.source_ref}, type: {ev.source_type})\n{ev.content}"
            for i, ev in enumerate(evidence))
        claim_lines = "\n".join(
            f"- [{c.category}] ({c.status}, trust={c.trust.level}) {c.text}" for c in claims)

        user = (f"Fund thesis (score through this lens):\n"
                f"{thesis.model_dump_json(indent=2)}\n\n"
                f"Claims:\n{claim_lines}\n\nEvidence excerpts:\n{numbered_evidence}")
        if cold_start is not None and self.axis == Axis.FOUNDER:
            user += (f"\n\nCold-start footprint assessment (public-footprint-only, "
                     f"aggregate {cold_start.aggregate:.0f}/100, "
                     f"known unknowns: {', '.join(cold_start.known_unknowns) or 'none'}):\n"
                     + "\n".join(f"- {name}: {d.score:.0f} — {d.rationale}"
                                 for name, d in cold_start.dimension_scores.items()))

        output = parse_structured(
            role="score", system=AXIS_PROMPTS[self.axis], user=user, schema=AxisOutput)

        avg_trust = (sum(c.trust.value for c in claims) / len(claims)) if claims else 0.0
        band = compute_band(
            output.score,
            evidence_count=len(evidence),
            avg_trust=avg_trust,
            distinct_source_types=len({ev.source_type for ev in evidence}),
        )

        history = self.score_repo.history(opportunity_id, self.axis)
        if not history:
            trend = Trend.INSUFFICIENT_HISTORY
        else:
            delta = output.score - history[-1].score
            trend = (Trend.STABLE if abs(delta) < 3
                     else Trend.IMPROVING if delta > 0 else Trend.DECLINING)

        cited = [evidence[i].id for i in output.key_evidence_indices
                 if 0 <= i < len(evidence)]
        axis_score = AxisScore(
            opportunity_id=opportunity_id, thesis_id=thesis.id, axis=self.axis,
            score=round(output.score, 1), confidence=band, trend=trend,
            market_stance=output.stance if self.axis == Axis.MARKET else None,
            rationale=output.rationale, evidence_ids=cited)
        self.score_repo.save(axis_score)

        self.trace.log(
            module=f"scoring.{self.axis.value}", step="axis_score",
            opportunity_id=opportunity_id, input_refs=[c.id for c in claims],
            output_refs=[axis_score.id], model=MODELS["score"],
            summary=f"{self.axis.value}={axis_score.score} "
                    f"[{band.low}-{band.high}] trend={trend.value}"
                    + (f" stance={output.stance}" if axis_score.market_stance else ""))
        return axis_score


def score_all_axes(opportunity_id: UUID, thesis: ThesisConfig, claims: list[Claim],
                   evidence: list[Evidence], score_repo: AxisScoreRepository,
                   trace: TraceLogger,
                   cold_start: ColdStartAssessment | None = None) -> list[AxisScore]:
    return [
        AxisScorer(axis, score_repo, trace).score(
            opportunity_id, thesis, claims, evidence, cold_start=cold_start)
        for axis in (Axis.FOUNDER, Axis.MARKET, Axis.IDEA_VS_MARKET)
    ]
