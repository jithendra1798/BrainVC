"""Seed the demo pipeline. Backend API must be running on :8000.

    cd backend && uv run python seeds/seed_demo.py

Creates a varied funnel (invest-worthy, escalate, gate-reject, off-thesis,
mid-funnel) plus a synthetic outbound founder pool with back-dated Founder
Score history so trends render on demo day (ARCHITECTURE §4). Synthetic
founders are labeled SYNTHETIC in evidence — honesty is the product.
"""

import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

API = "http://localhost:8000/api"
DECKS = Path(__file__).parent / "decks"

# (company, founder, email, one_liner, deck, mode)  mode: run | extract | apply
COMPANIES = [
    ("VectorHive", "Priya Raman", "priya@vectorhive.dev",
     "Inference routing that cuts enterprise LLM costs 61%", "vectorhive.md", "run"),
    ("MedLoop AI", "Elena Vasquez", "elena@medloop.health",
     "Prior authorization on autopilot for clinics", "medloop.md", "run"),
    ("QuantumYieldCoin", "Anonymous Founder", None,
     "AI quantum blockchain synergy", "quantumyield.md", "run"),
    ("PromptPantry", "Jonas Keller", "jonas@promptpantry.app",
     "Your AI sous-chef", "promptpantry.md", "run"),
    ("ShelfSense", "Omar Haddad", "omar@shelfsense.io",
     "Computer vision that catches out-of-stocks instantly", "shelfsense.md", "run"),
    ("DataForge", "Nadia Petrov", "nadia@dataforge.dev",
     "Self-healing data pipelines", "dataforge.md", "extract"),
    ("GreenGrid AI", "Wei Chen", "wei@greengrid.energy",
     "Feeder-level forecasting for distributed energy", "greengrid.md", "apply"),
]

SYNTHETIC_FOUNDERS = [
    # (name, github handle, score trajectory oldest->newest, bio)
    ("Mara Osei", "mara-osei-demo", [52, 58, 64],
     "Systems engineer; shipped two OSS observability tools; increasingly "
     "focused on applied AI infra."),
    ("Viktor Hale", "viktor-hale-demo", [61, 55, 49],
     "Former quant dev; public activity slowing over the last two quarters."),
    ("Lin Zhou", "lin-zhou-demo", [57, 58],
     "ML engineer; steady cadence of NLP side projects and technical writing."),
]


def apply_company(client, company, founder, email, one_liner, deck):
    data = {"company_name": company, "founder_name": founder}
    if email:
        data["founder_email"] = email
    if one_liner:
        data["one_liner"] = one_liner
    with open(DECKS / deck, "rb") as f:
        r = client.post(f"{API}/apply", data=data,
                        files={"deck": (deck, f, "text/markdown")})
    r.raise_for_status()
    return r.json()


def seed_companies():
    with httpx.Client(timeout=600) as client:
        for company, founder, email, one_liner, deck, mode in COMPANIES:
            t0 = time.time()
            applied = apply_company(client, company, founder, email, one_liner, deck)
            opp_id = applied["opportunity_id"]
            print(f"[apply]   {company}: {applied['evidence_created']} evidence "
                  f"({applied['evidence_deduplicated']} deduped)")
            if mode == "extract":
                r = client.post(f"{API}/opportunities/{opp_id}/extract")
                r.raise_for_status()
                print(f"[extract] {company}: {r.json()['claims_extracted']} claims "
                      f"({time.time() - t0:.0f}s)")
            elif mode == "run":
                r = client.post(f"{API}/opportunities/{opp_id}/run")
                r.raise_for_status()
                body = r.json()
                print(f"[run]     {company}: status={body['status']} "
                      f"rec={body.get('recommendation')} ({time.time() - t0:.0f}s)")
            else:
                print(f"[sourced] {company}: left at application stage")


def seed_founder_pool():
    from app.contracts.entities import FounderRecord
    from app.contracts.enums import SourceType
    from app.contracts.evidence import Evidence
    from app.contracts.scores import ConfidenceBand, FounderScoreEntry
    from app.ingestion.ingestor import content_hash
    from app.memory.db import get_session_factory
    from app.memory.repositories import (
        EvidenceRepository,
        FounderRepository,
        FounderScoreRepository,
    )

    session = get_session_factory()()
    founder_repo = FounderRepository(session)
    score_repo = FounderScoreRepository(session)
    evidence_repo = EvidenceRepository(session)
    now = datetime.now(timezone.utc)

    for name, handle, trajectory, bio in SYNTHETIC_FOUNDERS:
        if founder_repo.find_match(name=name):
            print(f"[pool]    {name}: already seeded, skipping")
            continue
        founder = founder_repo.save(FounderRecord(
            canonical_name=name, handles={"github": handle}, bio=bio))
        for i, text in enumerate([
            f"Synthetic profile: {name}. {bio}",
            f"Synthetic activity summary for {name}: repository cadence and "
            f"scope consistent with score trajectory {trajectory}.",
        ]):
            evidence_repo.save(Evidence(
                founder_id=founder.id, source_type=SourceType.SYNTHETIC,
                source_ref=f"synthetic://{handle}/{i}", content=text,
                content_hash=content_hash(text)))
        # Back-dated, append-only history so trends render (never fabricated
        # as real: source type + basis say synthetic).
        days_ago = [60, 30, 7][-len(trajectory):]
        for score, age in zip(trajectory, days_ago):
            score_repo.save(FounderScoreEntry(
                founder_id=founder.id, score=float(score),
                confidence=ConfidenceBand(
                    low=max(0, score - 12), high=min(100, score + 12),
                    basis="heuristic — synthetic seed profile"),
                inputs={"method": "synthetic_seed", "known_unknowns": ["synthetic profile"]},
                created_at=now - timedelta(days=age)))
        print(f"[pool]    {name}: {len(trajectory)} score entries "
              f"({trajectory[0]} -> {trajectory[-1]})")
    session.close()


if __name__ == "__main__":
    print("=== BrainVC demo seed ===")
    seed_founder_pool()
    seed_companies()
    print("=== done ===")
