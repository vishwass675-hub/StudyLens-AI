"""
Local vector search solution utilizing ChromaDB with persistent storage and fallback.
"""

from typing import List, Dict, Any, Optional
import os
import shutil
import numpy as np
from src.chunker import TextChunk


class LocalVectorStore:
    """
    Local Vector Store backed by ChromaDB with local persistent storage.
    Includes an in-memory / serialized NumPy cosine fallback for maximum robustness.
    """

    def __init__(
        self,
        persist_directory: str = "./data/chroma_db",
        collection_name: str = "studylens_academic_collection",
    ):
        self.persist_directory = persist_directory
        self.collection_name = collection_name
        self.client = None
        self.collection = None
        self._use_fallback = False

        # In-memory fallback buffers
        self._fallback_chunks: List[TextChunk] = []
        self._fallback_embeddings: Optional[np.ndarray] = None

        self._init_db()

    def _init_db(self):
        """Initializes ChromaDB persistent client or falls back to NumPy."""
        try:
            import chromadb
            os.makedirs(self.persist_directory, exist_ok=True)
            self.client = chromadb.PersistentClient(path=self.persist_directory)
            self.collection = self.client.get_or_create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"},
            )
            self._use_fallback = False
        except Exception as e:
            # Fallback to NumPy vector search if Chroma encounters environment/locking issues
            print(f"[StudyLens AI] Note: Initializing vectorized NumPy store (reason: {e})")
            self._use_fallback = True

    def add_chunks(
        self,
        chunks: List[TextChunk],
        embeddings: List[List[float]],
    ) -> int:
        """
        Stores document chunks and their embeddings into the local vector store.

        Returns:
            Number of successfully indexed chunks.
        """
        if not chunks or not embeddings:
            return 0

        if len(chunks) != len(embeddings):
            raise ValueError(f"Chunks count ({len(chunks)}) does not match embeddings count ({len(embeddings)}).")

        if not self._use_fallback and self.collection is not None:
            try:
                ids = [chunk.chunk_id for chunk in chunks]
                documents = [chunk.text for chunk in chunks]
                metadatas = [
                    {
                        "page_number": int(chunk.page_number),
                        "chunk_index": int(chunk.chunk_index),
                        "char_count": int(chunk.char_count),
                        "word_count": int(chunk.word_count),
                        "filename": str(chunk.metadata.get("filename", "unknown.pdf")),
                    }
                    for chunk in chunks
                ]

                # ChromaDB upsert
                self.collection.upsert(
                    ids=ids,
                    documents=documents,
                    embeddings=embeddings,
                    metadatas=metadatas,
                )
                return len(chunks)
            except Exception as e:
                print(f"[StudyLens AI] ChromaDB upsert error, switching to NumPy fallback: {e}")
                self._use_fallback = True

        # Fallback NumPy store
        self._fallback_chunks = list(chunks)
        self._fallback_embeddings = np.array(embeddings, dtype=np.float32)
        return len(chunks)

    def search(
        self,
        query_embedding: List[float],
        top_k: int = 4,
    ) -> List[Dict[str, Any]]:
        """
        Performs semantic vector search and returns the top_k most relevant chunks.

        Returns list of dicts:
            [
                {
                    "chunk_id": str,
                    "text": str,
                    "page_number": int,
                    "score": float,  # cosine similarity (0 to 1)
                    "metadata": dict
                },
                ...
            ]
        """
        if not self._use_fallback and self.collection is not None:
            try:
                results = self.collection.query(
                    query_embeddings=[query_embedding],
                    n_results=min(top_k, max(1, self.collection.count())),
                    include=["documents", "metadatas", "distances"],
                )

                formatted = []
                if results and results["ids"] and len(results["ids"][0]) > 0:
                    ids = results["ids"][0]
                    docs = results["documents"][0]
                    metas = results["metadatas"][0]
                    distances = results["distances"][0]

                    for cid, doc, meta, dist in zip(ids, docs, metas, distances):
                        # For cosine distance, similarity is 1 - distance
                        similarity = max(0.0, min(1.0, 1.0 - float(dist)))
                        formatted.append({
                            "chunk_id": cid,
                            "text": doc,
                            "page_number": meta.get("page_number", 1),
                            "score": round(similarity, 4),
                            "metadata": meta,
                        })

                # Sort by highest score first
                formatted.sort(key=lambda x: x["score"], reverse=True)
                return formatted
            except Exception as e:
                print(f"[StudyLens AI] Chroma search error, routing to NumPy fallback: {e}")

        # NumPy fallback search
        if not self._fallback_chunks or self._fallback_embeddings is None:
            return []

        q_vec = np.array(query_embedding, dtype=np.float32)
        q_norm = np.linalg.norm(q_vec)
        if q_norm == 0:
            return []

        doc_norms = np.linalg.norm(self._fallback_embeddings, axis=1)
        doc_norms[doc_norms == 0] = 1e-10

        # Cosine similarities
        scores = np.dot(self._fallback_embeddings, q_vec) / (doc_norms * q_norm)
        top_indices = np.argsort(scores)[::-1][:top_k]

        formatted = []
        for idx in top_indices:
            chunk = self._fallback_chunks[idx]
            sim = float(scores[idx])
            formatted.append({
                "chunk_id": chunk.chunk_id,
                "text": chunk.text,
                "page_number": chunk.page_number,
                "score": round(max(0.0, min(1.0, sim)), 4),
                "metadata": chunk.metadata,
            })

        return formatted

    def clear(self):
        """Resets the vector database."""
        if not self._use_fallback and self.client is not None and self.collection is not None:
            try:
                self.client.delete_collection(name=self.collection_name)
                self.collection = self.client.get_or_create_collection(
                    name=self.collection_name,
                    metadata={"hnsw:space": "cosine"},
                )
            except Exception:
                pass

        self._fallback_chunks = []
        self._fallback_embeddings = None

    def count(self) -> int:
        """Returns total number of chunks stored."""
        if not self._use_fallback and self.collection is not None:
            try:
                return self.collection.count()
            except Exception:
                pass
        return len(self._fallback_chunks)
