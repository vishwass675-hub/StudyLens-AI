"""
Document Repository for persistent SQLite storage.
Handles CRUD operations for documents and extracted pages.
"""

from typing import List, Optional
import datetime
from backend.app.db.database import db_manager, get_utc_now_iso
from backend.app.models.document import Document, DocumentStatus, ExtractedPage


class DocumentRepository:
    """Manages database persistence for academic documents and page texts."""

    def __init__(self, manager=None):
        self.db = manager or db_manager

    def save_document(self, doc: Document) -> None:
        """Inserts or updates document record in SQLite."""
        now = get_utc_now_iso()
        created = doc.created_at or now

        with self.db.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO documents (
                    id, filename, page_count, total_words, total_chars,
                    status, error_message, created_at, updated_at, last_accessed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    filename = excluded.filename,
                    page_count = excluded.page_count,
                    total_words = excluded.total_words,
                    total_chars = excluded.total_chars,
                    status = excluded.status,
                    error_message = excluded.error_message,
                    updated_at = excluded.updated_at,
                    last_accessed_at = excluded.last_accessed_at;
                """,
                (
                    doc.document_id,
                    doc.filename,
                    doc.page_count,
                    doc.total_words,
                    doc.total_chars,
                    doc.status.value if isinstance(doc.status, DocumentStatus) else doc.status,
                    doc.error_message,
                    created,
                    now,
                    now,
                ),
            )
            conn.commit()

    def get_document(self, document_id: str) -> Optional[Document]:
        """Retrieves document metadata by ID."""
        with self.db.get_connection() as conn:
            cur = conn.execute(
                """
                SELECT id, filename, page_count, total_words, total_chars,
                       status, error_message, created_at, updated_at, last_accessed_at
                FROM documents
                WHERE id = ?;
                """,
                (document_id,),
            )
            row = cur.fetchone()
            if not row:
                return None

            return Document(
                document_id=row["id"],
                filename=row["filename"],
                page_count=row["page_count"],
                total_words=row["total_words"],
                total_chars=row["total_chars"],
                status=DocumentStatus(row["status"]),
                error_message=row["error_message"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
                last_accessed_at=row["last_accessed_at"],
            )

    def list_documents(self) -> List[Document]:
        """Returns all documents ordered by last updated descending."""
        with self.db.get_connection() as conn:
            cur = conn.execute(
                """
                SELECT id, filename, page_count, total_words, total_chars,
                       status, error_message, created_at, updated_at, last_accessed_at
                FROM documents
                ORDER BY updated_at DESC;
                """
            )
            rows = cur.fetchall()
            return [
                Document(
                    document_id=r["id"],
                    filename=r["filename"],
                    page_count=r["page_count"],
                    total_words=r["total_words"],
                    total_chars=r["total_chars"],
                    status=DocumentStatus(r["status"]),
                    error_message=r["error_message"],
                    created_at=r["created_at"],
                    updated_at=r["updated_at"],
                    last_accessed_at=r["last_accessed_at"],
                )
                for r in rows
            ]

    def update_last_accessed(self, document_id: str) -> None:
        """Updates last_accessed_at timestamp."""
        now = get_utc_now_iso()
        with self.db.get_connection() as conn:
            conn.execute(
                "UPDATE documents SET last_accessed_at = ?, updated_at = ? WHERE id = ?;",
                (now, now, document_id),
            )
            conn.commit()

    def delete_document(self, document_id: str) -> bool:
        """Deletes a document and relies on ON DELETE CASCADE for foreign tables."""
        with self.db.get_connection() as conn:
            cur = conn.execute("DELETE FROM documents WHERE id = ?;", (document_id,))
            conn.commit()
            return cur.rowcount > 0

    def save_pages(self, pages: List[ExtractedPage]) -> None:
        """Saves extracted page texts for a document."""
        if not pages:
            return

        records = [
            (
                f"{p.document_id}_p{p.page}",
                p.document_id,
                p.page,
                p.text,
                p.char_count,
                p.word_count,
            )
            for p in pages
        ]

        with self.db.get_connection() as conn:
            conn.executemany(
                """
                INSERT OR REPLACE INTO pages (
                    id, document_id, page_number, page_text, char_count, word_count
                ) VALUES (?, ?, ?, ?, ?, ?);
                """,
                records,
            )
            conn.commit()

    def get_pages(self, document_id: str) -> List[ExtractedPage]:
        """Retrieves saved pages for a document."""
        with self.db.get_connection() as conn:
            cur = conn.execute(
                """
                SELECT document_id, page_number, page_text, char_count, word_count
                FROM pages
                WHERE document_id = ?
                ORDER BY page_number ASC;
                """,
                (document_id,),
            )
            rows = cur.fetchall()
            return [
                ExtractedPage(
                    document_id=r["document_id"],
                    page=r["page_number"],
                    text=r["page_text"],
                    char_count=r["char_count"],
                    word_count=r["word_count"],
                )
                for r in rows
            ]


# Global instance
document_repo = DocumentRepository()
