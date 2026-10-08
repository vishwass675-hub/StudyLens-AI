"""
Pydantic schemas for Conversation and Message persistence.
"""

from typing import List, Optional
from pydantic import BaseModel, Field
from backend.app.schemas.chat import SourceReference


class ConversationCreate(BaseModel):
    document_id: str = Field(..., description="ID of the document this conversation belongs to")
    title: Optional[str] = Field(default=None, description="Optional custom conversation title")


class ConversationUpdate(BaseModel):
    title: str = Field(..., min_length=1, max_length=120, description="New title for the conversation")


class MessageResponse(BaseModel):
    id: str
    conversation_id: str
    role: str
    content: str
    sources: List[SourceReference] = Field(default_factory=list)
    created_at: str


class ConversationResponse(BaseModel):
    id: str
    document_id: str
    document_filename: str
    title: str
    created_at: str
    updated_at: str
    message_count: int = 0


class ConversationListResponse(BaseModel):
    conversations: List[ConversationResponse]
