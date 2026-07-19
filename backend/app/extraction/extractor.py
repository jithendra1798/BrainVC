"""Extraction: Evidence → atomic, checkable Claims.

Separation of powers: this module CANNOT assign trust. Claims leave here
UNVERIFIED with skeptical default trust; only the Validator upgrades them.
"""

from uuid import UUID

from pydantic import BaseModel

from app.contracts.claims import Claim, EvidenceLink
from app.contracts.enums import ClaimCategory, Relation
from app.contracts.evidence import Evidence
from app.llm.client import parse_structured
from app.llm.config import MODELS
from app.memory.repositories import ClaimRepository
from app.trace.logger import TraceLogger

SYSTEM_PROMPT = """You extract factual claims from a startup's application materials.

Rules:
- Extract ATOMIC claims: one checkable assertion each (a number, a fact, a track-record item).
- Only assertions of fact the founder/company makes about themselves, their traction,
  revenue, team, product, or market. No opinions, no aspirations ("we will..."), no vision.
- Keep the claim text close to the source wording; do not embellish or infer.
- Every claim must cite the evidence excerpt(s) it came from via evidence_indices.
- If two excerpts state conflicting facts, extract BOTH claims separately — do not reconcile."""


class ExtractedClaim(BaseModel):
    category: ClaimCategory
    text: str
    evidence_indices: list[int]


class ExtractionOutput(BaseModel):
    claims: list[ExtractedClaim]


class ClaimExtractor:
    def __init__(self, claim_repo: ClaimRepository, trace: TraceLogger):
        self.claim_repo = claim_repo
        self.trace = trace

    def extract(self, opportunity_id: UUID, evidence: list[Evidence]) -> list[Claim]:
        numbered = "\n\n".join(
            f"[{i}] (source: {ev.source_ref})\n{ev.content}" for i, ev in enumerate(evidence)
        )
        output = parse_structured(
            role="extract",
            system=SYSTEM_PROMPT,
            user=f"Evidence excerpts:\n\n{numbered}",
            schema=ExtractionOutput,
        )

        claims: list[Claim] = []
        for item in output.claims:
            links = [
                EvidenceLink(evidence_id=evidence[i].id, relation=Relation.ASSERTS)
                for i in item.evidence_indices
                if 0 <= i < len(evidence)
            ]
            if not links:
                continue  # a claim with no traceable evidence does not enter the system
            claim = Claim(
                opportunity_id=opportunity_id,
                category=item.category,
                text=item.text,
                evidence_links=links,
            )
            self.claim_repo.save(claim)
            claims.append(claim)

        self.trace.log(
            module="extraction", step="extract_claims", opportunity_id=opportunity_id,
            input_refs=[ev.id for ev in evidence], output_refs=[c.id for c in claims],
            model=MODELS["extract"],
            summary=f"{len(claims)} claims extracted from {len(evidence)} evidence; "
                    f"all born UNVERIFIED/low-trust")
        return claims
