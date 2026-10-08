"""
Configuration settings for the StudyLens AI Backend.
"""

from pathlib import Path
from typing import List, Optional
import os
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "StudyLens AI PDF Ingestion & Tutor Backend"
    VERSION: str = "1.0.0"
    API_V1_PREFIX: str = "/api"

    # Directory for storing raw uploads safely
    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent
    DATA_DIR: Path = BASE_DIR / "data"
    UPLOAD_DIR: Path = DATA_DIR / "uploads"
    VECTOR_STORE_DIR: Path = DATA_DIR / "vector_store"
    DATABASE_PATH: Path = DATA_DIR / "studylens.db"

    # Allowed CORS Origins
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8501",
    ]

    # File Upload Constraints
    MAX_FILE_SIZE_MB: int = 50
    MAX_PAGES_LIMIT: int = 200

    # Default Chunking Parameters
    DEFAULT_CHUNK_SIZE: int = 1000
    DEFAULT_CHUNK_OVERLAP: int = 200
    MIN_CHUNK_SIZE: int = 100

    # Embedding & Retrieval Parameters
    EMBEDDING_MODEL: str = "local-minilm"
    EMBEDDING_DIMENSION: int = 384
    DEFAULT_TOP_K: int = 5
    SIMILARITY_THRESHOLD: float = 0.05

    # Ollama Cloud & Nemotron Configuration
    OLLAMA_API_KEY: Optional[str] = None
    OLLAMA_BASE_URL: str = "https://ollama.com"
    OLLAMA_MODEL: str = "nemotron-3-nano:30b-cloud"
    OLLAMA_TIMEOUT_SECONDS: float = 60.0
    MAX_CONVERSATION_TURNS: int = 6

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()

# Ensure directories exist
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
os.makedirs(settings.VECTOR_STORE_DIR, exist_ok=True)
