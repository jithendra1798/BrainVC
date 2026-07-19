"""Ingestion: RawSignal → persisted Evidence.

Dedup is global by content hash (v1 simplification: identical content seen
again is skipped, not re-linked — good enough for the demo, noted in trace).
Embeddings are computed lazily later (validator retrieval), not at ingest,
so ingestion never blocks on an API key.
"""

import hashlib
from uuid import UUID

from app.contracts.evidence import Evidence
from app.contracts.signals import RawSignal
from app.memory.repositories import EvidenceRepository
from app.trace.logger import TraceLogger


def content_hash(text: str) -> str:
    return hashlib.sha256(" ".join(text.split()).encode("utf-8")).hexdigest()


class IngestResult:
    def __init__(self, created: list[Evidence], deduped: int):
        self.created = created
        self.deduped = deduped


class Ingestor:
    def __init__(self, evidence_repo: EvidenceRepository, trace: TraceLogger):
        self.evidence_repo = evidence_repo
        self.trace = trace

    def ingest(self, signals: list[RawSignal], *, opportunity_id: UUID | None = None,
               founder_id: UUID | None = None) -> IngestResult:
        created: list[Evidence] = []
        deduped = 0
        for signal in signals:
            h = content_hash(signal.content)
            if self.evidence_repo.exists_hash(h):
                deduped += 1
                continue
            ev = Evidence(
                founder_id=founder_id,
                opportunity_id=opportunity_id,
                source_type=signal.source_type,
                source_ref=signal.source_ref,
                content=signal.content,
                content_hash=h,
                observed_at=signal.observed_at,
            )
            self.evidence_repo.save(ev)
            created.append(ev)

        self.trace.log(
            module="ingestion", step="ingest_signals", opportunity_id=opportunity_id,
            output_refs=[e.id for e in created],
            summary=f"{len(created)} evidence created, {deduped} deduplicated "
                    f"of {len(signals)} signals")
        return IngestResult(created, deduped)
