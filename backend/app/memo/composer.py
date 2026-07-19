"""Memo composer: validated claims + axis scores + thesis → investment memo.

Trust rules are code, not vibes:
- Claims are cited as [claim:N] index tokens and substituted to real UUIDs
  post-hoc — the model never invents a citation ID.
- Deterministic guardrail: if any revenue/traction claim is FLAGGED as
  contradicted, the recommendation can never be INVEST_100K.
- Gaps are explicit ("Cap table: not disclosed"), never fabricated numbers.
"""

import re
from uuid import UUID

from pydantic import BaseModel

from app.contracts.claims import Claim
from app.contracts.entities import CompanyRecord, FounderRecord
from app.contracts.enums import (
    ClaimCategory,
    ClaimStatus,
    Recommendation,
    SectionKind,
)
from app.contracts.memo import Memo, MemoSection
from app.contracts.scores import AxisScore
from app.contracts.thesis import ThesisConfig
from app.llm.client import parse_structured
from app.llm.config import MODELS
from app.memory.repositories import MemoRepository
from app.trace.logger import TraceLogger

SYSTEM_PROMPT = """You write evidence-backed investment memos for a venture fund.

Required sections (exactly these kinds): snapshot, hypotheses, swot,
problem_product, traction_kpis, bear_case.

Rules:
- Cite claims inline as [claim:N] where N is the claim's number. Cite every
  factual statement you rely on. Do not state facts that have no claim.
- Claims carry validator status + trust. Contradicted/flagged claims MUST be
  surfaced (in traction_kpis and bear_case), never smoothed over.
- NEVER invent data. Standard memo data that is missing (financials, cap table,
  customer references, churn, CAC) goes in `gaps` as explicit entries like
  "Cap table: not disclosed".
- bear_case is the adversarial view: the strongest honest argument against.
- Length: as brief as clarity allows; padding counts against the memo.
- recommendation: invest_100k, pass, or escalate_to_human (use escalate when
  evidence is contradictory or too thin for a confident yes/no)."""


class MemoSectionOut(BaseModel):
    kind: SectionKind
    markdown: str


class MemoOutput(BaseModel):
    sections: list[MemoSectionOut]
    gaps: list[str]
    recommendation: Recommendation
    recommendation_rationale: str


GUARDRAIL_CATEGORIES = {ClaimCategory.REVENUE, ClaimCategory.TRACTION}


class MemoComposer:
    def __init__(self, memo_repo: MemoRepository, trace: TraceLogger):
        self.memo_repo = memo_repo
        self.trace = trace

    def compose(self, opportunity_id: UUID, thesis: ThesisConfig,
                company: CompanyRecord, founder: FounderRecord | None,
                scores: list[AxisScore], claims: list[Claim]) -> Memo:
        claim_lines = "\n".join(
            f"({i}) [{c.category}] status={c.status} trust={c.trust.value:.2f}/"
            f"{c.trust.level} — {c.text}" for i, c in enumerate(claims))
        score_lines = "\n".join(
            f"- {s.axis}: {s.score} (band {s.confidence.low}-{s.confidence.high}, "
            f"trend {s.trend}"
            + (f", stance {s.market_stance}" if s.market_stance else "")
            + f") — {s.rationale}" for s in scores)

        output = parse_structured(
            role="memo", system=SYSTEM_PROMPT,
            user=f"Fund thesis:\n{thesis.model_dump_json(indent=2)}\n\n"
                 f"Company: {company.name}"
                 + (f" — {company.one_liner}" if company.one_liner else "") + "\n"
                 f"Founder: {founder.canonical_name if founder else 'unknown'}\n\n"
                 f"Axis scores (independent, never averaged):\n{score_lines}\n\n"
                 f"Validated claims:\n{claim_lines}",
            schema=MemoOutput)

        recommendation = output.recommendation
        rationale = output.recommendation_rationale
        flagged_core = [c for c in claims
                        if c.status == ClaimStatus.CONTRADICTED
                        and c.category in GUARDRAIL_CATEGORIES]
        if flagged_core and recommendation == Recommendation.INVEST_100K:
            recommendation = Recommendation.ESCALATE_TO_HUMAN
            rationale += (" [GUARDRAIL] Downgraded from invest_100k: "
                          f"{len(flagged_core)} contradicted revenue/traction claim(s) "
                          "must be resolved by a human before capital is deployed.")

        cited: set[UUID] = set()

        def substitute(match: re.Match) -> str:
            index = int(match.group(1))
            if 0 <= index < len(claims):
                cited.add(claims[index].id)
                return f"[claim:{claims[index].id}]"
            return ""  # citation to a nonexistent claim is dropped, not invented

        def resolve(text: str) -> str:
            return re.sub(r"\[claim:(\d+)\]", substitute, text)

        sections = [
            MemoSection(kind=s.kind, markdown=resolve(s.markdown))
            for s in output.sections
        ]

        memo = Memo(
            opportunity_id=opportunity_id, thesis_id=thesis.id,
            recommendation=recommendation, recommendation_rationale=resolve(rationale),
            sections=sections, claim_ids=sorted(cited, key=str),
            gaps=[resolve(g) for g in output.gaps])
        self.memo_repo.save(memo)

        self.trace.log(
            module="memo", step="compose_memo", opportunity_id=opportunity_id,
            input_refs=[c.id for c in claims] + [s.id for s in scores],
            output_refs=[memo.id], model=MODELS["memo"],
            summary=f"recommendation={recommendation.value} "
                    f"({len(sections)} sections, {len(cited)} claims cited, "
                    f"{len(output.gaps)} gaps flagged"
                    + (", guardrail applied" if flagged_core
                       and output.recommendation == Recommendation.INVEST_100K else "")
                    + ")")
        return memo
