"""
FastAPI application module alias for StudyLens AI backend.
Points directly to the primary backend entrypoint in backend.main.
"""

from backend.main import app

__all__ = ["app"]
