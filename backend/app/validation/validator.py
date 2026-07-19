"""Validator: the adversarial second opinion (brief stretch goal 2).

Runs a DIFFERENT model than the extractor (decorrelated errors), sees ALL
evidence — deck + any external web snippets — and issues a per-claim verdict.
Only this module may upgrade trust. Contradictions become persistent flags
that reach the memo before the investor (brief §7).
"""

from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel

from app.contracts.claims import Claim, ContradictionFlag, EvidenceLink, TrustScore
from app.contracts.enums import ClaimStatus, Relation, SourceType, TrustLevel
from app.contracts.evidence import Evidence
from app.llm.client import parse_structured
from app.llm.config import MODELS
from app.memory.repositories import ClaimRepository, EvidenceRepository
from app.trace.logger import TraceLogger
from app.validation.external import fetch_external_evidence, is_enabled

SYSTEM_PROMPT = """You are the adversarial VALIDATOR of a venture fund — the second
opinion that keeps the primary analyst honest. For EACH claim, cross-reference it
against ALL evidence excerpts and judge:

- supported: independent evidence (a DIFFERENT source than the one asserting it)
  corroborates the claim.
- contradicted: some evidence conflicts with the claim. Numbers that cannot both
  be true (e.g. "$40K MRR" vs "pre-revenue") are contradictions — flag BOTH claims.
- unverifiable: the claim rests solely on its own assertion. This is the honest
  default for self-reported deck content.

trust_value is the probability the claim is true AS STATED given the evidence
(0.0-1.0). A single self-reported assertion with no corroboration caps around
0.5 even if plausible. Never let a deck slide corroborate itself."""


class VerdictStatus(StrEnum):
    SUPPORTED = "supported"
    CONTRADICTED = "contradicted"
    UNVERIFIABLE = "unverifiable"


class ClaimVerdict(BaseModel):
    claim_index: int
    status: VerdictStatus
    trust_value: float
    rationale: str  # one sentence, cite evidence indices like [4]
    supporting_evidence_indices: list[int]
    contradicting_evidence_indices: list[int]


class ValidationOutput(BaseModel):
    verdicts: list[ClaimVerdict]


def _level(status: VerdictStatus, value: float) -> TrustLevel:
    if status == VerdictStatus.CONTRADICTED:
        return TrustLevel.FLAGGED
    if value >= 0.7:
        return TrustLevel.HIGH
    if value >= 0.4:
        return TrustLevel.MEDIUM
    return TrustLevel.LOW


class Validator:
    def __init__(self, claim_repo: ClaimRepository, evidence_repo: EvidenceRepository,
                 trace: TraceLogger):
        self.claim_repo = claim_repo
        self.evidence_repo = evidence_repo
        self.trace = trace

    def validate(self, opportunity_id: UUID, claims: list[Claim],
                 evidence: list[Evidence]) -> list[Claim]:
        external = fetch_external_evidence(claims, opportunity_id, self.evidence_repo)
        all_evidence = evidence + external

        numbered_evidence = "\n\n".join(
            f"[{i}] (source: {ev.source_ref}, type: {ev.source_type})\n{ev.content}"
            for i, ev in enumerate(all_evidence))
        numbered_claims = "\n".join(
            f"({i}) [{c.category}] {c.text}" for i, c in enumerate(claims))

        output = parse_structured(
            role="validate", system=SYSTEM_PROMPT,
            user=f"Claims to validate:\n{numbered_claims}\n\n"
                 f"Evidence excerpts:\n{numbered_evidence}\n\n"
                 f"Return one verdict per claim, claim_index 0..{len(claims) - 1}.",
            schema=ValidationOutput)

        method = ("internal cross-reference + external web (Tavily)"
                  if external else "internal cross-reference (LLM)")
        updated: list[Claim] = []
        flags = 0
        for verdict in output.verdicts:
            if not 0 <= verdict.claim_index < len(claims):
                continue
            claim = claims[verdict.claim_index]
            claim.status = ClaimStatus(verdict.status.value)
            claim.trust = TrustScore(
                value=round(max(0.0, min(1.0, verdict.trust_value)), 2),
                level=_level(verdict.status, verdict.trust_value),
                rationale=verdict.rationale, verification_method=method)
            existing = {link.evidence_id for link in claim.evidence_links}
            for i in verdict.supporting_evidence_indices:
                if 0 <= i < len(all_evidence) and all_evidence[i].id not in existing:
                    claim.evidence_links.append(EvidenceLink(
                        evidence_id=all_evidence[i].id, relation=Relation.SUPPORTS))
            for i in verdict.contradicting_evidence_indices:
                if 0 <= i < len(all_evidence):
                    if all_evidence[i].id not in existing:
                        claim.evidence_links.append(EvidenceLink(
                            evidence_id=all_evidence[i].id, relation=Relation.CONTRADICTS))
                    self.claim_repo.save_flag(ContradictionFlag(
                        claim_id=claim.id, conflicting_evidence_id=all_evidence[i].id,
                        note=verdict.rationale))
                    flags += 1
            self.claim_repo.save(claim)
            updated.append(claim)

        self.trace.log(
            module="validation", step="validate_claims", opportunity_id=opportunity_id,
            input_refs=[c.id for c in claims], output_refs=[c.id for c in updated],
            model=MODELS["validate"],
            summary=f"{len(updated)} claims validated ({method}); "
                    f"{sum(1 for c in updated if c.status == ClaimStatus.CONTRADICTED)} "
                    f"contradicted, {flags} contradiction flags; "
                    f"external evidence: {len(external)} "
                    f"(tavily {'on' if is_enabled() else 'off'})")
        return updated
