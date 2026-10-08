"""
Local persistent vector store using SQLite and NumPy.
Stores dense vector embeddings, chunk text, document provenance, and page numbers.
Supports document-level isolation and fast cosine similarity retrieval.
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from pathlib import Path
import sqlite3
import json
import numpy as np

from backend.app.models.document import DocumentChunk
from backend.app.core.config import settings


@dataclass
class VectorSearchResult:
    """Represents a chunk retrieved from the vector store with similarity score."""
    chunk_id: str
    document_id: str
    page: int
    filename: str
    text: str
    score: float
    metadata: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "chunk_id": self.chunk_id,
            "document_id": self.document_id,
            "page": self.page,
            "filename": self.filename,
            "text": self.text,
            "score": round(self.score, 4),
            "metadata": self.metadata,
        }


class LocalVectorStore:
    """
    Persistent local vector database.
    Stores vectors as binary float32 blobs in SQLite, allowing fast querying,
    persistence across restarts, and guaranteed document-level filtering.
    """

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or (settings.VECTOR_STORE_DIR / "vectors.db")
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        """Initializes database schema and indexes."""
        with self._get_connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS document_chunks (
                    chunk_id TEXT PRIMARY KEY,
                    document_id TEXT NOT NULL,
                    filename TEXT NOT NULL,
                    page_number INTEGER NOT NULL,
                    chunk_index INTEGER NOT NULL,
                    chunk_text TEXT NOT NULL,
                    char_count INTEGER,
                    word_count INTEGER,
                    embedding BLOB NOT NULL,
                    metadata_json TEXT
                )
                """
            )
            # Create index for fast document_id filtering
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_doc_id ON document_chunks (document_id)"
            )
            conn.commit()

    def has_document(self, document_id: str) -> bool:
        """Checks if a document is already indexed in the vector store."""
        with self._get_connection() as conn:
            cur = conn.execute(
                "SELECT 1 FROM document_chunks WHERE document_id = ? LIMIT 1",
                (document_id,),
            )
            return cur.fetchone() is not None

    def insert_chunks(
        self,
        document_id: str,
        filename: str,
        chunks: List[DocumentChunk],
        embeddings: List[List[float]],
    ) -> int:
        """
        Inserts chunks and their embeddings into the vector store.
        Avoids redundant re-indexing if already indexed.
        """
        if not chunks or not embeddings:
            return 0

        if len(chunks) != len(embeddings):
            raise ValueError("Chunks count must match embeddings count.")

        with self._get_connection() as conn:
            # Delete existing chunks for this document if updating
            conn.execute(
                "DELETE FROM document_chunks WHERE document_id = ?",
                (document_id,),
            )

            records = []
            for chunk, emb in zip(chunks, embeddings):
                # Convert embedding to float32 bytes
                emb_bytes = np.array(emb, dtype=np.float32).tobytes()
                meta_json = json.dumps({"filename": filename, "page": chunk.page_number})

                records.append(
                    (
                        chunk.chunk_id,
                        document_id,
                        filename,
                        chunk.page_number,
                        chunk.chunk_index,
                        chunk.chunk_text,
                        chunk.char_count,
                        chunk.word_count,
                        emb_bytes,
                        meta_json,
                    )
                )

            conn.executemany(
                """
                INSERT INTO document_chunks (
                    chunk_id, document_id, filename, page_number, chunk_index,
                    chunk_text, char_count, word_count, embedding, metadata_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                records,
            )
            conn.commit()

        return len(chunks)

    def search(
        self,
        document_id: str,
        query_embedding: List[float],
        top_k: int = 5,
    ) -> List[VectorSearchResult]:
        """
        Searches chunks filtered strictly by document_id and ranked by cosine similarity.
        """
        with self._get_connection() as conn:
            cur = conn.execute(
                """
                SELECT chunk_id, document_id, filename, page_number, chunk_text, embedding, metadata_json
                FROM document_chunks
                WHERE document_id = ?
                """,
                (document_id,),
            )
            rows = cur.fetchall()

        if not rows:
            return []

        # Vectorized similarity computation
        q_vec = np.array(query_embedding, dtype=np.float32)
        q_norm = np.linalg.norm(q_vec)
        if q_norm == 0:
            return []
        q_unit = q_vec / q_norm

        embeddings_list = []
        for r in rows:
            arr = np.frombuffer(r["embedding"], dtype=np.float32)
            embeddings_list.append(arr)

        matrix = np.vstack(embeddings_list)  # (N, D)
        matrix_norms = np.linalg.norm(matrix, axis=1, keepdims=True)
        matrix_norms[matrix_norms == 0] = 1e-10
        matrix_unit = matrix / matrix_norms

        # Cosine similarities
        scores = np.dot(matrix_unit, q_unit)  # (N,)

        # Sort indices descending
        ranked_indices = np.argsort(scores)[::-1][:top_k]

        results: List[VectorSearchResult] = []
        for idx in ranked_indices:
            row = rows[idx]
            score_val = float(scores[idx])
            meta = json.loads(row["metadata_json"]) if row["metadata_json"] else {}

            results.append(
                VectorSearchResult(
                    chunk_id=row["chunk_id"],
                    document_id=row["document_id"],
                    page=row["page_number"],
                    filename=row["filename"],
                    text=row["chunk_text"],
                    score=score_val,
                    metadata=meta,
                )
            )

        return results

    def delete_document(self, document_id: str) -> int:
        """Deletes all chunks for a specific document."""
        with self._get_connection() as conn:
            cur = conn.execute(
                "DELETE FROM document_chunks WHERE document_id = ?",
                (document_id,),
            )
            conn.commit()
            return cur.rowcount

    def count(self, document_id: Optional[str] = None) -> int:
        """Returns the number of stored chunks."""
        with self._get_connection() as conn:
            if document_id:
                cur = conn.execute(
                    "SELECT COUNT(*) FROM document_chunks WHERE document_id = ?",
                    (document_id,),
                )
            else:
                cur = conn.execute("SELECT COUNT(*) FROM document_chunks")
            return cur.fetchone()[0]

    def clear(self):
        """Clears all vectors from the store."""
        with self._get_connection() as conn:
            conn.execute("DELETE FROM document_chunks")
            conn.commit()


# Global singleton instance
vector_store = LocalVectorStore()
