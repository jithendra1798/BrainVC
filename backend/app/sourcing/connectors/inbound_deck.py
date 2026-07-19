"""Inbound deck connector: PDF or markdown deck → one RawSignal per slide.

Markdown decks are first-class (risk R-1): slides split on `---` lines,
falling back to `##` headings. PDFs parse per page via pypdf.
"""

import re
from pathlib import Path

from app.contracts.enums import SourceType
from app.contracts.signals import ConnectorQuery, RawSignal


class InboundDeckConnector:
    source_type = SourceType.DECK_SLIDE

    def fetch(self, query: ConnectorQuery) -> list[RawSignal]:
        path = Path(query.params["path"])
        founder_hint = query.params.get("founder")
        company_hint = query.params.get("company")

        if path.suffix.lower() == ".pdf":
            chunks = self._parse_pdf(path)
        else:
            chunks = self._parse_markdown(path.read_text(encoding="utf-8"))

        return [
            RawSignal(
                source_type=self.source_type,
                source_ref=f"{path.name}#slide={i + 1}",
                content=chunk,
                founder_hint=founder_hint,
                company_hint=company_hint,
            )
            for i, chunk in enumerate(chunks)
        ]

    @staticmethod
    def _parse_pdf(path: Path) -> list[str]:
        from pypdf import PdfReader

        reader = PdfReader(str(path))
        return [t for page in reader.pages if (t := (page.extract_text() or "").strip())]

    @staticmethod
    def _parse_markdown(text: str) -> list[str]:
        slides = [s.strip() for s in re.split(r"\n-{3,}\n", text) if s.strip()]
        if len(slides) > 1:
            return slides
        parts = re.split(r"(?m)^(?=## )", text)
        return [p.strip() for p in parts if p.strip()]
