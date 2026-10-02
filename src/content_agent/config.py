from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = ROOT / "config"
OUTPUT_DIR = ROOT / "output"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT / ".env", extra="ignore")

    # "claude_code": run the Claude Code CLI headless, billed to your Pro/Max plan.
    # "api": call the Claude API directly with ANTHROPIC_API_KEY (pay per token).
    llm_backend: Literal["claude_code", "api"] = "claude_code"
    claude_cli: str = "claude"
    # From `claude setup-token`; only needed where you can't log in with a browser (VPS).
    claude_code_oauth_token: str = ""
    claude_model: str = "claude-opus-5-5"
    database_url: str = f"sqlite:///{ROOT / 'data' / 'content_agent.db'}"
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""
    min_relevance_score: int = 7
    # Leave empty to use Playwright's own Chromium (`playwright install chromium`).
    chromium_path: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()
