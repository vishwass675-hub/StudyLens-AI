"""
Pydantic API schemas for request and response models.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from backend.app.models.document import DocumentStatus


class DocumentUploadResponse(BaseModel):
    document_id: str
    filename: str
    page_count: int
    status: DocumentStatus
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    last_accessed_at: Optional[str] = None

    model_config = {
        "json_schema_extra": {
            "example": {
                "document_id": "doc_a8f9c12b",
                "filename": "DBMS_Notes.pdf",
                "page_count": 42,
                "status": "ready",
            }
        }
    }


class DocumentDetailResponse(BaseModel):
    document_id: str
    filename: str
    page_count: int
    total_words: int
    total_chars: int
    total_chunks: int
    status: DocumentStatus
    error_message: Optional[str] = None
    created_at: str
    updated_at: Optional[str] = None
    last_accessed_at: Optional[str] = None


class PageResponse(BaseModel):
    document_id: str
    page: int
    text: str
    char_count: int
    word_count: int


class ChunkResponse(BaseModel):
    document_id: str
    chunk_id: str
    page_number: int
    chunk_index: int
    chunk_text: str
    char_count: int
    word_count: int


class DocumentListResponse(BaseModel):
    documents: List[DocumentDetailResponse]


class HealthResponse(BaseModel):
    status: str = "ok"


# ==============================================================================
# Search & Semantic Retrieval Schemas
# ==============================================================================
class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, description="Natural language search query")
    top_k: Optional[int] = Field(None, ge=1, le=50, description="Number of relevant chunks to retrieve")
    similarity_threshold: Optional[float] = Field(None, ge=0.0, le=1.0, description="Minimum relevance score threshold")

    model_config = {
        "json_schema_extra": {
            "example": {
                "query": "Explain database normalization and third normal form",
                "top_k": 5,
            }
        }
    }


class SearchResultItem(BaseModel):
    chunk_id: str
    document_id: str
    page: int
    filename: str
    text: str
    score: float
    metadata: Optional[Dict[str, Any]] = None


class SearchResponse(BaseModel):
    document_id: str
    query: str
    relevant_found: bool
    results_count: int
    results: List[SearchResultItem]
    message: Optional[str] = None
