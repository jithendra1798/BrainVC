import json
from pathlib import Path

from app.contracts.thesis import ThesisConfig
from app.memory.repositories import ThesisRepository

PRESET_DIR = Path(__file__).parent / "presets"
DEFAULT_PRESET = "maschmeyer_demo.json"


def load_preset(filename: str = DEFAULT_PRESET) -> ThesisConfig:
    data = json.loads((PRESET_DIR / filename).read_text())
    return ThesisConfig.model_validate(data)


class ThesisProvider:
    """Thin config holder. Zero reasoning lives here — by design."""

    def __init__(self, repo: ThesisRepository):
        self.repo = repo

    def get_active(self) -> ThesisConfig:
        active = self.repo.get_active()
        if active is None:
            active = self.repo.save(load_preset(), make_active=True)
        return active

    def set_active(self, config: ThesisConfig) -> ThesisConfig:
        return self.repo.save(config, make_active=True)
