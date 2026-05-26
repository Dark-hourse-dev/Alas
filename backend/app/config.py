"""
ALAS Configuration — Central settings management.
All configuration is loaded from environment variables with sensible defaults.
"""

from pathlib import Path
from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # --- Ollama / LLM ---
    ollama_host: str = "http://localhost:11434"
    ollama_model: str = "llama3.2:3b"
    embedding_model: str = "nomic-embed-text"

    # --- Memory ---
    chroma_persist_dir: str = "./backend/data/chroma"
    sqlite_db_path: str = "./backend/data/alas.db"
    max_memory_results: int = 10

    # --- Voice ---
    whisper_model_size: str = "base"
    tts_voice: str = "en-US-AriaNeural"

    # --- Server ---
    host: str = "0.0.0.0"
    port: int = 8000
    cors_origins: list[str] = ["http://localhost:8000", "http://localhost:3000"]

    # --- Safety ---
    safety_enabled: bool = True

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache
def get_settings() -> Settings:
    """Get cached application settings."""
    return Settings()


def ensure_data_dirs():
    """Create required data directories if they don't exist."""
    settings = get_settings()
    Path(settings.chroma_persist_dir).mkdir(parents=True, exist_ok=True)
    Path(settings.sqlite_db_path).parent.mkdir(parents=True, exist_ok=True)
