"""Entity resolution v1 — deliberately conservative (risk R-4):
exact email/handle match, then normalized-name match. Anything fuzzier is
out of scope; ambiguity creates a new record rather than a wrong merge."""

from app.contracts.entities import CompanyRecord, FounderRecord
from app.memory.repositories import CompanyRepository, FounderRepository


class EntityResolver:
    def __init__(self, founder_repo: FounderRepository, company_repo: CompanyRepository):
        self.founder_repo = founder_repo
        self.company_repo = company_repo

    def resolve_or_create_founder(self, *, name: str, email: str | None = None,
                                  handles: dict[str, str] | None = None) -> FounderRecord:
        match = self.founder_repo.find_match(name=name, email=email, handles=handles or {})
        if match:
            merged = False
            if email and email not in match.emails:
                match.emails.append(email)
                merged = True
            for k, v in (handles or {}).items():
                if k not in match.handles:
                    match.handles[k] = v
                    merged = True
            if merged:
                self.founder_repo.save(match)
            return match
        founder = FounderRecord(
            canonical_name=name, emails=[email] if email else [], handles=handles or {})
        return self.founder_repo.save(founder)

    def resolve_or_create_company(self, *, name: str, one_liner: str | None = None) -> CompanyRecord:
        match = self.company_repo.find_by_name(name)
        if match:
            return match
        return self.company_repo.save(CompanyRecord(name=name, one_liner=one_liner))
