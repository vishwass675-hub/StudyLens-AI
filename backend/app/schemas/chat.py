"""
Pydantic schemas for the StudyLens AI Chat Tutor API.
"""

from typing import List, Optional
from pydantic import BaseModel, Field
from backend.app.core.prompts import TutorMode


class ConversationMessage(BaseModel):
    role: str = Field(..., description="'user' or 'assistant'")
    content: str = Field(..., description="Message text")


class SourceReference(BaseModel):
    document: str = Field(..., description="Filename of source PDF")
    page: int = Field(..., description="1-indexed source page number")


class TutorChatRequest(BaseModel):
    document_id: str = Field(..., description="ID of the active document")
    message: str = Field(..., min_length=1, description="Student's question or message")
    mode: Optional[TutorMode] = Field(default=TutorMode.SIMPLE, description="Tutor pedagogical mode")
    conversation: Optional[List[ConversationMessage]] = Field(
        default_factory=list, description="Prior conversation context turns"
    )
    top_k: Optional[int] = Field(default=5, ge=1, le=20, description="Max chunks to retrieve")
    similarity_threshold: Optional[float] = Field(
        default=None, ge=0.0, le=1.0, description="Minimum relevance score threshold"
    )
    conversation_id: Optional[str] = Field(
        default=None, description="Optional conversation session ID for persistence"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "document_id": "doc_123",
                "message": "Explain third normal form",
                "mode": "simple",
                "conversation": [],
                "conversation_id": "conv_123",
            }
        }
    }


class TutorChatResponse(BaseModel):
    answer: str = Field(..., description="Grounded tutor response")
    sources: List[SourceReference] = Field(
        default_factory=list,
        description="List of document pages that contributed to the answer",
    )
    conversation_id: Optional[str] = Field(
        default=None, description="Associated conversation session ID"
    )
