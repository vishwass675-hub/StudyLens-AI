"""
Document ingestion and lifecycle management service.
Coordinates validation, extraction, chunking, embedding generation, vector indexing,
and SQLite persistence.
"""

from typing import Dict, List, Optional
import os
import uuid
from pathlib import Path
from fastapi import UploadFile

from backend.app.models.document import Document, DocumentStatus, ExtractedPage, DocumentChunk
from backend.app.services.pdf_service import PDFService, InvalidPDFError, EmptyPDFError
from backend.app.services.chunking_service import ChunkingService
from backend.app.services.embedding_service import EmbeddingService, embedding_service
from backend.app.services.vector_store import LocalVectorStore, vector_store
from backend.app.repositories.document_repository import DocumentRepository, document_repo
from backend.app.repositories.study_results_repository import study_results_repo
from backend.app.core.config import settings


class DocumentService:
    """Manages document storage, extraction, chunking, embedding, vector persistence, and deletion."""

    def __init__(
        self,
        pdf_svc: Optional[PDFService] = None,
        chunking_svc: Optional[ChunkingService] = None,
        embedding_svc: Optional[EmbeddingService] = None,
        vector_st: Optional[LocalVectorStore] = None,
        doc_repository: Optional[DocumentRepository] = None,
    ):
        self.pdf_service = pdf_svc or PDFService()
        self.chunking_service = chunking_svc or ChunkingService()
        self.embedding_service = embedding_svc or embedding_service
        self.vector_store = vector_st or vector_store
        self.repo = doc_repository or document_repo
        # In-memory runtime cache for quick access
        self._documents: Dict[str, Document] = {}

    def _generate_document_id(self) -> str:
        """Generates a clean, unique document identifier."""
        return f"doc_{uuid.uuid4().hex[:12]}"

    async def ingest_document(
        self,
        file: UploadFile,
        chunk_size: Optional[int] = None,
        chunk_overlap: Optional[int] = None,
    ) -> Document:
        """
        Executes full ingestion & vector indexing pipeline:
        1. Validates PDF extension & magic bytes
        2. Assigns unique document_id
        3. Saves PDF safely
        4. Extracts text page-by-page preserving page numbers
        5. Generates chunks with overlap
        6. Generates dense vector embeddings
        7. Indexes vectors in persistent local vector store
        8. Persists metadata and pages in SQLite database
        9. Transitions status to 'ready' (or 'failed' on error)
        """
        filename = file.filename or "document.pdf"

        # 1. Basic validation
        if not filename.lower().endswith(".pdf"):
            raise InvalidPDFError(f"File '{filename}' is not a PDF. Only .pdf files are accepted.")

        # Read content
        content = await file.read()
        max_bytes = settings.MAX_FILE_SIZE_MB * 1024 * 1024
        if len(content) > max_bytes:
            raise InvalidPDFError(
                f"File '{filename}' exceeds maximum allowed size of {settings.MAX_FILE_SIZE_MB}MB."
            )

        if not content.startswith(b"%PDF"):
            raise InvalidPDFError(f"File '{filename}' does not contain valid PDF data.")

        doc_id = self._generate_document_id()

        # Initialize document with 'uploaded' status
        doc_record = Document(
            document_id=doc_id,
            filename=filename,
            status=DocumentStatus.UPLOADED,
        )
        self._documents[doc_id] = doc_record
        self.repo.save_document(doc_record)

        # 2. Save file safely
        save_path = settings.UPLOAD_DIR / f"{doc_id}.pdf"
        try:
            with open(save_path, "wb") as f:
                f.write(content)
        except Exception as e:
            doc_record.status = DocumentStatus.FAILED
            doc_record.error_message = f"Failed to save document: {str(e)}"
            self.repo.save_document(doc_record)
            raise

        # 3. Transition to 'processing'
        doc_record.status = DocumentStatus.PROCESSING
        self.repo.save_document(doc_record)

        try:
            # 4. Extract pages using PyMuPDF
            pages = self.pdf_service.extract_pages(
                document_id=doc_id,
                file_input=content,
                filename=filename,
            )

            # Persist pages in SQLite
            self.repo.save_pages(pages)

            # 5. Create chunks
            chunks = self.chunking_service.create_chunks(
                document_id=doc_id,
                pages=pages,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
            )

            if not chunks:
                raise EmptyPDFError(f"No usable text chunks produced from '{filename}'.")

            # 6. Generate embeddings
            chunk_texts = [c.chunk_text for c in chunks]
            embeddings = self.embedding_service.embed_documents(chunk_texts)

            if len(embeddings) != len(chunks):
                raise RuntimeError("Mismatch between generated embeddings count and chunks count.")

            # 7. Store embeddings and chunks in local persistent vector store
            self.vector_store.insert_chunks(
                document_id=doc_id,
                filename=filename,
                chunks=chunks,
                embeddings=embeddings,
            )

            # Update document aggregate and mark READY
            doc_record.pages = pages
            doc_record.chunks = chunks
            doc_record.page_count = len(pages)
            doc_record.total_words = sum(p.word_count for p in pages)
            doc_record.total_chars = sum(p.char_count for p in pages)
            doc_record.status = DocumentStatus.READY

            # Persist finalized metadata in SQLite
            self.repo.save_document(doc_record)

            return doc_record

        except (InvalidPDFError, EmptyPDFError) as e:
            doc_record.status = DocumentStatus.FAILED
            doc_record.error_message = str(e)
            self.repo.save_document(doc_record)
            raise
        except Exception as e:
            doc_record.status = DocumentStatus.FAILED
            doc_record.error_message = f"Ingestion pipeline failed: {str(e)}"
            self.repo.save_document(doc_record)
            raise

    def get_document(self, document_id: str) -> Optional[Document]:
        """Retrieves a document by its unique ID from memory or SQLite."""
        if document_id in self._documents:
            return self._documents[document_id]

        doc = self.repo.get_document(document_id)
        if doc:
            # Rehydrate pages and chunks
            pages = self.repo.get_pages(document_id)
            doc.pages = pages
            self._documents[document_id] = doc
            return doc
        return None

    def list_documents(self) -> List[Document]:
        """Returns all documents from SQLite persistence."""
        docs = self.repo.list_documents()
        # Sync in-memory cache
        for d in docs:
            if d.document_id not in self._documents:
                self._documents[d.document_id] = d
        return docs

    def get_document_pages(self, document_id: str) -> Optional[List[ExtractedPage]]:
        """Retrieves extracted pages for a document."""
        doc = self.get_document(document_id)
        if not doc:
            return None
        if not doc.pages:
            doc.pages = self.repo.get_pages(document_id)
        return doc.pages

    def get_document_chunks(self, document_id: str) -> Optional[List[DocumentChunk]]:
        """Retrieves created chunks for a document."""
        doc = self.get_document(document_id)
        if not doc:
            return None

        if not doc.chunks:
            # Recreate chunks from pages if not already in memory
            pages = self.get_document_pages(document_id)
            if pages:
                doc.chunks = self.chunking_service.create_chunks(
                    document_id=document_id,
                    pages=pages,
                )
        return doc.chunks

    def delete_document(self, document_id: str) -> bool:
        """
        Safely deletes document and all associated data:
        1. Remove from vector store
        2. Remove cached study results
        3. Remove SQLite records (cascading pages, conversations, messages)
        4. Remove stored PDF file
        5. Invalidate memory cache
        """
        # 1. Remove vector store entries
        self.vector_store.delete_document(document_id)

        # 2. Remove cached study results in SQLite
        study_results_repo.delete_for_document(document_id)

        # 3. Remove SQLite document record
        success = self.repo.delete_document(document_id)

        # 4. Remove physical PDF upload if present
        pdf_path = settings.UPLOAD_DIR / f"{document_id}.pdf"
        if pdf_path.exists():
            try:
                pdf_path.unlink()
            except Exception:
                pass

        # 5. Clear memory cache
        if document_id in self._documents:
            del self._documents[document_id]

        return success


# Global singleton instance
document_service = DocumentService()
