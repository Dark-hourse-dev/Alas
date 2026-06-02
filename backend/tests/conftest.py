import pytest
import os
from pathlib import Path

# Set environment variables for testing before loading settings
os.environ["ALAS_SAFETY_ENABLED"] = "true"
os.environ["ALAS_ENCRYPTION_SALT"] = "test_salt_1234567890_test_salt_123"

from backend.app.config import get_settings

@pytest.fixture(autouse=True)
def setup_test_env(tmp_path):
    """Override persistence directories to use temporary paths for tests."""
    settings = get_settings()
    
    # Store originals
    orig_chroma = settings.chroma_persist_dir
    orig_sqlite = settings.sqlite_db_path
    
    # Set to temp paths
    settings.chroma_persist_dir = str(tmp_path / "chroma")
    settings.sqlite_db_path = str(tmp_path / "sqlite" / "alas.db")
    
    yield settings
    
    # Restore
    settings.chroma_persist_dir = orig_chroma
    settings.sqlite_db_path = orig_sqlite
