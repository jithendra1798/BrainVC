"""Voice briefing via ElevenLabs — 'your AI analyst reads you the decision.'
Dormant until ELEVENLABS_API_KEY is set (same pattern as Tavily). Generated
audio is cached under data/briefs/ so the demo never waits twice."""

import os
import re
from pathlib import Path

import httpx

from app.contracts.claims import Claim
from app.contracts.enums import ClaimStatus
from app.contracts.memo import Memo

VOICE_ID = os.environ.get("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM")  # Rachel
MODEL_ID = os.environ.get("ELEVENLABS_MODEL", "eleven_flash_v2_5")
BRIEF_DIR = Path(__file__).resolve().parents[2] / "data" / "briefs"


def is_enabled() -> bool:
    return bool(os.environ.get("ELEVENLABS_API_KEY"))


def _strip_tokens(text: str) -> str:
    return re.sub(r"\s*\[claim:[a-f0-9-]+\]", "", text)


def briefing_text(company_name: str, memo: Memo, claims: list[Claim]) -> str:
    contradicted = sum(1 for c in claims if c.status == ClaimStatus.CONTRADICTED)
    rec = memo.recommendation.value.replace("_", " ")
    rationale = _strip_tokens(memo.recommendation_rationale)
    if len(rationale) > 550:
        rationale = rationale[:550].rsplit(". ", 1)[0] + "."
    gaps = "; ".join(memo.gaps[:2])
    parts = [
        f"BrainVC briefing for {company_name}.",
        f"Recommendation: {rec}.",
        rationale,
        f"{len(claims)} claims analyzed, {contradicted} contradicted.",
    ]
    if gaps:
        parts.append(f"Top declared gaps: {gaps}.")
    return " ".join(parts)


def synthesize(text: str) -> bytes:
    response = httpx.post(
        f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}",
        params={"output_format": "mp3_44100_128"},
        headers={"xi-api-key": os.environ["ELEVENLABS_API_KEY"]},
        json={"text": text, "model_id": MODEL_ID},
        timeout=60,
    )
    response.raise_for_status()
    return response.content


def brief_path(opportunity_id: str) -> Path:
    BRIEF_DIR.mkdir(parents=True, exist_ok=True)
    return BRIEF_DIR / f"{opportunity_id}.mp3"
