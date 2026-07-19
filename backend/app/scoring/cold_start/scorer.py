"""Cold-start scorer: founder potential from PUBLIC FOOTPRINT ALONE.

The answer to the brief's cold-start warning (FAQ 10) and Area of Research 3.
LLM rubric over five dimensions, each with cited evidence; known_unknowns are
first-class output — the system says what it could NOT observe. Result is
persisted as an append-only FounderScoreEntry: the founder 'credit score'
that persists across applications and never resets.

Research framing (documented for the README): to test footprint→success
prediction, freeze assessments at time T, track funded/failed outcomes at
T+18mo, and measure rank correlation per dimension — the same rubric,
retrospectively falsifiable.
"""

import math
from uuid import UUID

from pydantic import BaseModel

from app.contracts.entities import FounderRecord
from app.contracts.evidence import Evidence
from app.contracts.scores import (
    ColdStartAssessment,
    ConfidenceBand,
    DimensionScore,
    FounderScoreEntry,
)
from app.llm.client import parse_structured
from app.llm.config import MODELS
from app.memory.repositories import FounderScoreRepository
from app.trace.logger import TraceLogger

DIMENSIONS = ["shipping_velocity", "technical_depth", "learning_rate",
              "public_communication", "domain_signal"]

SYSTEM_PROMPT = """You assess a founder's POTENTIAL from their public footprint
alone — no traction, no revenue, no warm intro. Score five dimensions (0-100):

- shipping_velocity: do they finish and ship things? Frequency and recency of
  completed artifacts beats raw activity.
- technical_depth: evidence of hard technical work (non-trivial repos, systems
  work, papers). Stars/followers are weak proxies — weight substance.
- learning_rate: trajectory over time — new domains, growing scope, improving
  craft between artifacts.
- public_communication: can they explain their work (READMEs, bios, writing)?
- domain_signal: footprint coherence toward a domain where they'd have an edge.

Rules:
- Cite evidence indices for every dimension rationale.
- Score ONLY what the evidence shows. If a dimension is barely observable,
  score it near the middle with a short rationale and add it to known_unknowns.
- known_unknowns: list what you could NOT observe (e.g. "no public writing",
  "no collaboration signals", "employment history unverified"). Be exhaustive —
  honesty here is the product."""


class DimensionOut(BaseModel):
    name: str
    score: float
    rationale: str
    evidence_indices: list[int]


class ColdStartOutput(BaseModel):
    dimensions: list[DimensionOut]
    known_unknowns: list[str]


class ColdStartScorer:
    def __init__(self, founder_score_repo: FounderScoreRepository, trace: TraceLogger):
        self.founder_score_repo = founder_score_repo
        self.trace = trace

    def assess(self, founder: FounderRecord,
               evidence: list[Evidence]) -> ColdStartAssessment:
        numbered = "\n\n".join(
            f"[{i}] (source: {ev.source_ref}, observed: "
            f"{ev.observed_at.date() if ev.observed_at else 'unknown'})\n{ev.content}"
            for i, ev in enumerate(evidence))
        output = parse_structured(
            role="score", system=SYSTEM_PROMPT,
            user=f"Founder: {founder.canonical_name} "
                 f"(handles: {founder.handles})\n\nPublic footprint evidence:\n{numbered}",
            schema=ColdStartOutput)

        dimension_scores: dict[str, DimensionScore] = {}
        for dim in output.dimensions:
            key = dim.name.lower().strip().replace(" ", "_")
            if key not in DIMENSIONS:
                continue
            dimension_scores[key] = DimensionScore(
                score=round(dim.score, 1), rationale=dim.rationale,
                evidence_ids=[evidence[i].id for i in dim.evidence_indices
                              if 0 <= i < len(evidence)])
        aggregate = (sum(d.score for d in dimension_scores.values())
                     / len(dimension_scores)) if dimension_scores else 0.0

        # Band: honest heuristic — footprint breadth + unknowns drive width.
        # Unknowns term saturates: past ~8 unknowns the band is already "we
        # know very little"; an unbounded term just destroys the signal.
        half = 6.0
        half += 14.0 * min(1.0, len(output.known_unknowns) / 8.0)
        half += 10.0 / max(1.0, math.sqrt(max(len(evidence), 1)))
        band = ConfidenceBand(
            low=max(0.0, round(aggregate - half, 1)),
            high=min(100.0, round(aggregate + half, 1)),
            basis=f"heuristic — {len(evidence)} footprint items, "
                  f"{len(output.known_unknowns)} known unknowns")

        assessment = ColdStartAssessment(
            founder_id=founder.id, dimension_scores=dimension_scores,
            aggregate=round(aggregate, 1), confidence=band,
            evidence_ids=[ev.id for ev in evidence],
            known_unknowns=output.known_unknowns)

        # Persist to the append-only Founder Score history (never resets).
        self.founder_score_repo.save(FounderScoreEntry(
            founder_id=founder.id, score=assessment.aggregate,
            confidence=band,
            inputs={
                "method": "cold_start_footprint_rubric_v1",
                "dimension_scores": {k: v.model_dump(mode="json")
                                     for k, v in dimension_scores.items()},
                "known_unknowns": output.known_unknowns,
            }))

        self.trace.log(
            module="scoring.cold_start", step="footprint_assessment",
            input_refs=[ev.id for ev in evidence], model=MODELS["score"],
            summary=f"founder={founder.canonical_name} aggregate={assessment.aggregate} "
                    f"[{band.low}-{band.high}], "
                    f"{len(output.known_unknowns)} known unknowns")
        return assessment


def rebuild_assessment(entry: FounderScoreEntry) -> ColdStartAssessment:
    """Rebuild an assessment from persisted FounderScoreEntry.inputs (Memory,
    not recomputation) so the founder axis can consume it across applications."""
    inputs = entry.inputs or {}
    return ColdStartAssessment(
        founder_id=entry.founder_id,
        dimension_scores={k: DimensionScore.model_validate(v)
                          for k, v in inputs.get("dimension_scores", {}).items()},
        aggregate=entry.score, confidence=entry.confidence,
        known_unknowns=inputs.get("known_unknowns", []))
