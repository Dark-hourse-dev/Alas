"""
ALAS Configuration — Central settings management.
All configuration is loaded from environment variables with sensible defaults.
"""

import secrets
import logging
from pathlib import Path
from functools import lru_cache
from pydantic_settings import BaseSettings

logger = logging.getLogger("alas.config")

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
    encryption_salt: str = "alas_secure_salt_2026_default_please_change"
    
    # --- Cloud Fallback ---
    cloud_api_key: str = ""
    cloud_api_url: str = "https://api.openai.com/v1/chat/completions"
    cloud_model: str = "gpt-4o"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache
def get_settings() -> Settings:
    """Get cached application settings."""
    return Settings()

def validate_security(settings: Settings):
    """Validates that security-critical settings are not using unsafe defaults."""
    warnings = []
    
    if settings.encryption_salt == "alas_secure_salt_2026_default_please_change":
        warnings.append("Using default encryption_salt! Memory Vault is vulnerable.")
        
    if "*" in settings.cors_origins:
        warnings.append("CORS origins allows '*'. This is unsafe for production.")
        
    if not settings.cloud_api_key:
        logger.info("ℹ️ Cloud API key is empty. Cloud Engine fallback will be disabled.")

    for warning in warnings:
        logger.warning(f"⚠️ SECURITY WARNING: {warning}")

def ensure_data_dirs():
    """Create required data directories if they don't exist."""
    settings = get_settings()
    Path(settings.chroma_persist_dir).mkdir(parents=True, exist_ok=True)
    Path(settings.sqlite_db_path).parent.mkdir(parents=True, exist_ok=True)
