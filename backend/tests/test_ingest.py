import io
from uuid import uuid4

from fastapi.testclient import TestClient

from app.api.main import app


def _deck_bytes(nonce: str) -> bytes:
    # Inline deck with a per-test nonce in every slide, so content hashes are
    # unique per test session (dedup is global by design — same founder
    # re-applying with the same deck is the demoable case).
    slides = [
        f"# TestCo {nonce}\n\nAI for testing pipelines.",
        f"## Traction {nonce}\n\n$10K MRR from 3 pilots.",
        f"## Team {nonce}\n\nJo Smith, ex-BigCo infra.",
    ]
    return "\n\n---\n\n".join(slides).encode()


def _apply(client: TestClient, deck: bytes):
    return client.post(
        "/api/apply",
        data={"company_name": "TestCo", "founder_name": "Jo Smith",
              "founder_email": "jo@testco.dev"},
        files={"deck": ("testco.md", io.BytesIO(deck), "text/markdown")},
    )


def test_apply_ingests_deck_and_dedups():
    client = TestClient(app)
    deck = _deck_bytes(uuid4().hex[:8])

    r1 = _apply(client, deck)
    assert r1.status_code == 200, r1.text
    body = r1.json()
    assert body["slides_parsed"] == 3
    assert body["evidence_created"] == 3
    assert body["evidence_deduplicated"] == 0

    # Same deck again: new opportunity, but every slide dedups on content hash.
    body2 = _apply(client, deck).json()
    assert body2["evidence_created"] == 0
    assert body2["evidence_deduplicated"] == 3
    # Entity resolution: same founder+email must NOT create a duplicate person.
    assert body2["founder_id"] == body["founder_id"]

    # Evidence carries provenance and is queryable per opportunity.
    detail = client.get(f"/api/opportunities/{body['opportunity_id']}").json()
    assert len(detail["evidence"]) == 3
    ev = detail["evidence"][0]
    assert ev["source_type"] == "deck_slide"
    assert "#slide=" in ev["source_ref"]
    assert ev["retrieved_at"] is not None

    # Trace log recorded the sourcing + ingestion steps.
    trace = client.get(f"/api/opportunities/{body['opportunity_id']}/trace").json()
    modules = {t["module"] for t in trace}
    assert "sourcing.inbound_deck" in modules
    assert "ingestion" in modules


def test_thesis_default_preset_active():
    client = TestClient(app)
    thesis = client.get("/api/thesis").json()
    assert thesis["check_size_usd"] == 100_000
    assert thesis["risk_posture"] == "back_potential_over_traction"
