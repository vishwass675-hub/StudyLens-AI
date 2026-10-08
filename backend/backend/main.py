"""Expose the app for Render's existing ``backend.main:app`` command."""

from main import app

__all__ = ["app"]
