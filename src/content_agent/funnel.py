"""Lead funnel settings (config/funnel.yaml): the comment keyword and Roy's booking link."""

from dataclasses import dataclass

import yaml

from content_agent.config import CONFIG_DIR


@dataclass(frozen=True)
class Funnel:
    keyword: str
    booking_url: str


def load_funnel(path=CONFIG_DIR / "funnel.yaml") -> Funnel:
    data = yaml.safe_load(path.read_text()) or {}
    return Funnel(
        keyword=str(data.get("keyword") or "GUIDE").strip().upper(),
        booking_url=str(data.get("booking_url") or "").strip(),
    )
