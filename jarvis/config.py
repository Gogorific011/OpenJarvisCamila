from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=None, extra="ignore")

    groq_api_key: str = ""
    fish_api_key: str = ""
    fish_voice_id: str = ""
    fish_model: str = "s2.1-pro"
    fish_speed: float = Field(default=1.0, ge=0.5, le=2.0)
    jarvis_access_token: str = ""
    jarvis_address_as: str = ""
    jarvis_model: str = "llama-3.3-70b-versatile"
    jarvis_agent: Literal["simple", "orchestrator"] = "simple"
    jarvis_debug: bool = False
    jarvis_host: str = "127.0.0.1"
    jarvis_port: int = 8787
    jarvis_max_requests_per_minute: int = 30
    jarvis_enable_memory: bool = False


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    missing = []
    if not settings.groq_api_key:
        missing.append(
            "GROQ_API_KEY: add your key from https://console.groq.com to .env"
        )
    if not settings.fish_api_key:
        missing.append("FISH_API_KEY: add your key from https://fish.audio to .env")
    if missing:
        print("J.A.R.V.I.S. configuration incomplete:\n  - " + "\n  - ".join(missing))
    return settings


def configure_logging() -> None:
    settings = get_settings()
    logging.basicConfig(
        level=logging.DEBUG if settings.jarvis_debug else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
