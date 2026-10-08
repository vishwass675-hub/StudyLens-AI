"""
Internal domain models for documents, extracted pages, and chunks.
"""

from enum import Enum
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime, timezone


class DocumentStatus(str, Enum):
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"


@dataclass
class ExtractedPage:
    """Represents text extracted from a single PDF page."""
    document_id: str
    page: int  # 1-indexed page number
    text: str
    char_count: int
    word_count: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "document_id": self.document_id,
            "page": self.page,
            "text": self.text,
            "char_count": self.char_count,
            "word_count": self.word_count,
        }


@dataclass
class DocumentChunk:
    """Represents a text chunk partitioned for semantic retrieval."""
    document_id: str
    chunk_id: str
    page_number: int
    chunk_index: int
    chunk_text: str
    char_count: int
    word_count: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "document_id": self.document_id,
            "chunk_id": self.chunk_id,
            "page_number": self.page_number,
            "chunk_index": self.chunk_index,
            "chunk_text": self.chunk_text,
            "char_count": self.char_count,
            "word_count": self.word_count,
        }


@dataclass
class Document:
    """Complete document aggregate tracking status, pages, and chunks."""
    document_id: str
    filename: str
    page_count: int = 0
    status: DocumentStatus = DocumentStatus.UPLOADED
    total_words: int = 0
    total_chars: int = 0
    error_message: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: Optional[str] = None
    last_accessed_at: Optional[str] = None
    pages: List[ExtractedPage] = field(default_factory=list)
    chunks: List[DocumentChunk] = field(default_factory=list)
