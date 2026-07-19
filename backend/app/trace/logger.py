from uuid import UUID

from app.contracts.trace import TraceEntry
from app.memory.repositories import TraceRepository


class TraceLogger:
    def __init__(self, repo: TraceRepository):
        self.repo = repo

    def log(self, *, module: str, step: str, opportunity_id: UUID | None = None,
            input_refs: list[UUID] | None = None, output_refs: list[UUID] | None = None,
            model: str | None = None, summary: str = "") -> TraceEntry:
        return self.repo.save(TraceEntry(
            opportunity_id=opportunity_id, module=module, step=step,
            input_refs=input_refs or [], output_refs=output_refs or [],
            model=model, summary=summary))
