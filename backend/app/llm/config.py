"""Central model configuration. Role-specialized tiers (DECISIONS D-4):
every role is env-overridable so a model swap never touches module code."""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

MODELS = {
    # gate: mini, not nano — a false negative at the gate is the most
    # expensive error a fund can make; judgment beats the marginal cent.
    "gate": os.environ.get("BRAINVC_MODEL_GATE", "gpt-5.4-mini"),
    "extract": os.environ.get("BRAINVC_MODEL_EXTRACT", "gpt-5.4-mini"),
    "score": os.environ.get("BRAINVC_MODEL_SCORE", "gpt-5.5"),
    "validate": os.environ.get("BRAINVC_MODEL_VALIDATE", "gpt-5.5"),
    "memo": os.environ.get("BRAINVC_MODEL_MEMO", "gpt-5.5"),
    "embed": os.environ.get("BRAINVC_MODEL_EMBED", "text-embedding-3-small"),
}
