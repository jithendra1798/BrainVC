"""External verification via Tavily. Dormant until TAVILY_API_KEY is set —
then market-category claims get web snippets ingested as first-class WEB
Evidence (provenance = result URL) and cross-referenced like any other source."""

import os
from uuid import UUID

import httpx

from app.contracts.claims import Claim
from app.contracts.enums import ClaimCategory, SourceType
from app.contracts.evidence import Evidence
from app.ingestion.ingestor import content_hash
from app.memory.repositories import EvidenceRepository

TAVILY_URL = "https://api.tavily.com/search"
MAX_CLAIMS = 3
MAX_RESULTS_PER_CLAIM = 3


def is_enabled() -> bool:
    return bool(os.environ.get("TAVILY_API_KEY"))


def fetch_external_evidence(claims: list[Claim], opportunity_id: UUID,
                            evidence_repo: EvidenceRepository) -> list[Evidence]:
    if not is_enabled():
        return []
    checkable = [c for c in claims if c.category == ClaimCategory.MARKET][:MAX_CLAIMS]
    created: list[Evidence] = []
    for claim in checkable:
        try:
            response = httpx.post(TAVILY_URL, json={
                "api_key": os.environ["TAVILY_API_KEY"],
                "query": claim.text,
                "max_results": MAX_RESULTS_PER_CLAIM,
            }, timeout=20)
            response.raise_for_status()
            results = response.json().get("results", [])
        except Exception:  # noqa: BLE001 — external lookup is best-effort, never fatal
            continue
        for r in results:
            text = (r.get("content") or "").strip()
            if not text:
                continue
            h = content_hash(text)
            if evidence_repo.exists_hash(h):
                continue
            ev = Evidence(
                opportunity_id=opportunity_id, source_type=SourceType.WEB,
                source_ref=r.get("url", "web"), content=text, content_hash=h)
            evidence_repo.save(ev)
            created.append(ev)
    return created
