"""
Standardized Error Taxonomy and Application Exceptions for StudyLens AI.
Provides uniform machine-readable error codes and safe human-readable messages.
"""

from enum import Enum
from typing import Optional, Dict, Any
from fastapi import HTTPException, status


class ErrorCode(str, Enum):
    INVALID_FILE = "INVALID_FILE"
    DOCUMENT_PROCESSING_FAILED = "DOCUMENT_PROCESSING_FAILED"
    DOCUMENT_NOT_FOUND = "DOCUMENT_NOT_FOUND"
    DOCUMENT_NOT_READY = "DOCUMENT_NOT_READY"
    CONVERSATION_NOT_FOUND = "CONVERSATION_NOT_FOUND"
    CONVERSATION_MISMATCH = "CONVERSATION_MISMATCH"
    RETRIEVAL_FAILED = "RETRIEVAL_FAILED"
    LLM_AUTH_FAILED = "LLM_AUTH_FAILED"
    LLM_RATE_LIMIT = "LLM_RATE_LIMIT"
    LLM_TIMEOUT = "LLM_TIMEOUT"
    LLM_GENERATION_FAILED = "LLM_GENERATION_FAILED"
    DATABASE_ERROR = "DATABASE_ERROR"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    INTERNAL_SERVER_ERROR = "INTERNAL_SERVER_ERROR"


class AppException(HTTPException):
    """
    Standardized Application Exception for consistent API error responses.
    Produces responses matching:
    {
      "detail": "Human readable message",
      "error": {
        "code": "ERROR_CODE",
        "message": "Human readable message"
      }
    }
    """

    def __init__(
        self,
        code: ErrorCode,
        message: str,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        headers: Optional[Dict[str, str]] = None,
    ):
        super().__init__(status_code=status_code, detail=message, headers=headers)
        self.code = code
        self.message = message

    def to_dict(self) -> Dict[str, Any]:
        return {
            "detail": self.message,
            "error": {
                "code": self.code.value,
                "message": self.message,
            },
        }
