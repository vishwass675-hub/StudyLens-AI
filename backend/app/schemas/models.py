"""
Pydantic schemas for StudyLens AI FastAPI service.
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class DocumentMetadata(BaseModel):
    filename: str
    total_pages: int
    total_words: int
    total_chars: int
    total_chunks: int
    status: str = "ready"


class SourceExcerpt(BaseModel):
    chunk_id: str
    text: str
    page_number: int
    score: float
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ChatMessageSchema(BaseModel):
    id: str
    role: str  # "user" | "assistant"
    content: str
    sources: Optional[List[SourceExcerpt]] = None
    created_at: Optional[str] = None


class ChatRequest(BaseModel):
    question: str
    document_id: Optional[str] = None
    provider: Optional[str] = "gemini"
    model_name: Optional[str] = None
    api_key: Optional[str] = None
    top_k: Optional[int] = 4
    history: Optional[List[Dict[str, str]]] = Field(default_factory=list)


class ChatResponse(BaseModel):
    answer: str
    sources: List[SourceExcerpt]
    model_name: str
    provider: str


class DocumentListResponse(BaseModel):
    documents: List[DocumentMetadata]
    active_document: Optional[DocumentMetadata] = None


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
