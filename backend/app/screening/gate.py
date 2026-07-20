"""Viability gate: fast, cheap first-pass filter (brief §4 'Screen').

Sees the RAW application (deck slides), not atomized claims — a gate judging
a bullet list of extracted claims mistakes atomization for incoherence.
Rejection is a first-class, traced outcome — never a silent drop.

Calibration principle: the false negative is the most expensive error a fund
can make. This gate exists to kill nonsense, not to do diligence."""

from uuid import UUID

from pydantic import BaseModel

from app.contracts.evidence import Evidence
from app.contracts.thesis import ThesisConfig
from app.llm.client import parse_structured
from app.llm.config import MODELS
from app.trace.logger import TraceLogger

SYSTEM_PROMPT = """You are the first-pass viability gate of a venture fund.
Your ONLY job: reject clearly non-viable applications. Three valid reasons:
1. Incoherent — no identifiable product or business can be discerned.
2. Obvious scam — guaranteed returns, anonymous teams soliciting funds,
   pressure tactics, technobabble with nothing behind it.
3. Total thesis mismatch on ALL THREE of sector AND geography AND stage.

What is explicitly NOT grounds for rejection (downstream stages handle these):
- Sector, geography, or stage mismatch alone — scoring surfaces that as a PASS
  with full analysis. Gates that reject on sector are how funds miss Uber and
  Coinbase.
- Unsubstantiated claims, ambitious projections, thin traction, or missing
  metrics — universal in pre-seed decks; the validator and diligence stage
  exist precisely to test them.
- Anachronism: some applications are archival decks that state their year
  (e.g. 2008). Evaluate them in their stated era's context.
- Garbled or fragmented text (split words like "T equila", interleaved
  columns, orphaned numbers next to unrelated labels): that is OUR PDF
  extraction failing, not the founder being incoherent. Judge only the
  substance you can discern through the noise; if a real product, team, or
  market is visible, it passes — note the extraction noise in your reason
  instead of blaming the applicant for it.

When in doubt, let it through. Be strict about nonsense, generous about
ambition."""


class GateOutput(BaseModel):
    viable: bool
    reason: str


class ViabilityGate:
    def __init__(self, trace: TraceLogger):
        self.trace = trace

    def screen(self, opportunity_id: UUID, thesis: ThesisConfig,
               evidence: list[Evidence]) -> GateOutput:
        slides = "\n\n".join(
            f"[{ev.source_ref}]\n{ev.content}" for ev in evidence)
        result = parse_structured(
            role="gate",
            system=SYSTEM_PROMPT,
            user=f"Fund thesis:\n{thesis.model_dump_json(indent=2)}\n\n"
                 f"Application materials:\n{slides}\n\n"
                 f"Is this clearly non-viable (incoherent, scam, or total "
                 f"three-way thesis mismatch)?",
            schema=GateOutput,
        )
        self.trace.log(
            module="screening.gate", step="viability_gate", opportunity_id=opportunity_id,
            input_refs=[ev.id for ev in evidence], model=MODELS["gate"],
            summary=f"viable={result.viable}: {result.reason}")
        return result
