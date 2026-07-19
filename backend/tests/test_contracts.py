from uuid import uuid4

from app.contracts.claims import Claim, EvidenceLink, TrustScore
from app.contracts.enums import ClaimCategory, ClaimStatus, Relation, TrustLevel
from app.thesis.provider import load_preset


def test_claim_round_trip():
    claim = Claim(
        opportunity_id=uuid4(),
        category=ClaimCategory.REVENUE,
        text="NimbusOps has $40K MRR from 12 design partners.",
        evidence_links=[EvidenceLink(evidence_id=uuid4(), relation=Relation.ASSERTS)],
    )
    # Claims are born skeptical
    assert claim.status == ClaimStatus.UNVERIFIED
    assert claim.trust.level == TrustLevel.LOW

    restored = Claim.model_validate_json(claim.model_dump_json())
    assert restored == claim


def test_trust_score_defaults_are_skeptical():
    trust = TrustScore()
    assert trust.value <= 0.3
    assert trust.verification_method == "single-source, unverified"


def test_maschmeyer_preset_loads():
    thesis = load_preset()
    assert thesis.check_size_usd == 100_000
    assert "US" in thesis.geographies
    assert thesis.risk_posture == "back_potential_over_traction"
