"""Environment-based application configuration."""

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    app_name: str = "TouchGrass"
    ollama_base_url: str = "http://127.0.0.1:11434"
    ollama_model: str = "qwen2.5-coder:3b"
    ollama_timeout_seconds: float = 90.0


def get_settings() -> Settings:
    """Load application settings from the process environment."""
    project_root = Path(__file__).resolve().parents[2]
    load_dotenv(project_root / ".env")
    return Settings(
        app_name=os.getenv("TOUCHGRASS_APP_NAME", "TouchGrass"),
        ollama_base_url=os.getenv(
            "OLLAMA_BASE_URL", "http://127.0.0.1:11434"
        ).rstrip("/"),
        ollama_model=os.getenv("OLLAMA_MODEL", "qwen2.5-coder:3b"),
        ollama_timeout_seconds=float(os.getenv("OLLAMA_TIMEOUT_SECONDS", "90")),
    )
