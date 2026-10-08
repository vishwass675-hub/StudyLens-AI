"""
Health and readiness check routes for StudyLens AI.
Separates basic liveness (is server running) from deep readiness (DB, vector store, LLM).
"""

from typing import Dict, Any
from fastapi import APIRouter
from pydantic import BaseModel

from backend.app.core.config import settings
from backend.app.db.database import db_manager
from backend.app.services.vector_store import vector_store

router = APIRouter(prefix="/health", tags=["Health"])


class LivenessResponse(BaseModel):
    status: str = "ok"


class ReadinessResponse(BaseModel):
    status: str
    database: str
    vector_store: str
    llm_configured: bool
    model: str


@router.get("", response_model=LivenessResponse, summary="Basic liveness check")
def health_liveness():
    """Confirms the FastAPI backend is running and accepting HTTP requests."""
    return LivenessResponse()


@router.get("/ready", response_model=ReadinessResponse, summary="Deep readiness verification")
def health_readiness():
    """
    Checks operational dependencies:
    - SQLite database connection
    - Vector store availability
    - Ollama Cloud configuration status
    """
    db_status = "unavailable"
    try:
        with db_manager.get_connection() as conn:
            cur = conn.execute("SELECT 1;")
            if cur.fetchone()[0] == 1:
                db_status = "connected"
    except Exception:
        db_status = "error"

    vs_status = "available" if settings.VECTOR_STORE_DIR.exists() else "uninitialized"
    llm_ready = bool(settings.OLLAMA_API_KEY and settings.OLLAMA_API_KEY.strip())

    overall_status = "ready" if (db_status == "connected" and vs_status == "available") else "degraded"

    return ReadinessResponse(
        status=overall_status,
        database=db_status,
        vector_store=vs_status,
        llm_configured=llm_ready,
        model=settings.OLLAMA_MODEL,
    )
