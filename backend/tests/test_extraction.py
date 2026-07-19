"""Live-API smoke test: skipped when no OPENAI_API_KEY (CI-safe, venue-ready)."""

import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.llm.config import MODELS  # noqa: F401 — importing loads .env
from app.api.main import app

SEED_DECK = Path(__file__).resolve().parents[1] / "seeds" / "decks" / "nimbusops.md"

pytestmark = pytest.mark.skipif(
    not os.environ.get("OPENAI_API_KEY"), reason="OPENAI_API_KEY not set")


def test_extract_claims_from_deck():
    client = TestClient(app)
    with open(SEED_DECK, "rb") as f:
        applied = client.post(
            "/api/apply",
            data={"company_name": "NimbusOps-X", "founder_name": "Ada Vance"},
            files={"deck": ("nimbusops-x.md", f, "text/markdown")},
        ).json()

    r = client.post(f"/api/opportunities/{applied['opportunity_id']}/extract")
    assert r.status_code == 200, r.text
    claims = r.json()["claims"]
    assert len(claims) >= 5

    for c in claims:
        # every claim is traceable and born skeptical
        assert c["evidence_links"], c["text"]
        assert c["status"] == "unverified"
        assert c["trust"]["level"] == "low"

    # the seeded contradiction must surface as TWO separate claims, not one reconciled
    texts = " || ".join(c["text"].lower() for c in claims)
    assert "40k" in texts or "$40" in texts
    assert "pre-revenue" in texts
