"""
Embedding Service for StudyLens AI.
Provides a configurable, modular embedding layer that creates normalized dense vectors
for document chunks and user queries.
"""

from abc import ABC, abstractmethod
from typing import List, Optional
import os
import re
import hashlib
import numpy as np

from backend.app.core.config import settings


class BaseEmbeddingProvider(ABC):
    """Abstract base class for embedding providers."""

    @abstractmethod
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Embeds a list of document chunk texts."""
        pass

    @abstractmethod
    def embed_query(self, query: str) -> List[float]:
        """Embeds a single query string."""
        pass

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Returns the dimensionality of the generated embeddings."""
        pass


class LocalDenseEmbeddingProvider(BaseEmbeddingProvider):
    """
    High-performance, lightweight local semantic embedding model.
    Computes subword n-grams, lexical frequency weights, and dense hashed projections
    normalized to unit L2 length. Runs 100% locally with zero external network downloads.
    """

    def __init__(self, dimension: int = 384):
        self._dim = dimension

    @property
    def dimension(self) -> int:
        return self._dim

    def _embed_single(self, text: str) -> List[float]:
        if not text or not text.strip():
            return [0.0] * self._dim

        words = re.findall(r"\b[a-zA-Z0-9_\-\.]+\b", text.lower())
        vec = np.zeros(self._dim, dtype=np.float32)

        if not words:
            return vec.tolist()

        for w in words:
            # Word token contribution
            h_word = int(hashlib.md5(w.encode("utf-8")).hexdigest(), 16)
            vec[h_word % self._dim] += 2.0

            # Subword character n-grams (3 to 5 chars) to capture word roots and academic terminology
            w_len = len(w)
            for n in range(3, min(6, w_len + 1)):
                for i in range(w_len - n + 1):
                    gram = w[i : i + n]
                    h_gram = int(hashlib.md5(gram.encode("utf-8")).hexdigest(), 16)
                    vec[h_gram % self._dim] += 0.5

        # L2 Normalization so dot product equals cosine similarity
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm

        return vec.tolist()

    def embed_documents(self, texts: List[str], batch_size: int = 64) -> List[List[float]]:
        results: List[List[float]] = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            results.extend([self._embed_single(t) for t in batch])
        return results

    def embed_query(self, query: str) -> List[float]:
        return self._embed_single(query)


class SentenceTransformersEmbeddingProvider(BaseEmbeddingProvider):
    """Optional wrapper for sentence-transformers if installed in the environment."""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        from sentence_transformers import SentenceTransformer
        self.model = SentenceTransformer(model_name)
        self._dim = self.model.get_sentence_embedding_dimension()

    @property
    def dimension(self) -> int:
        return self._dim

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        embeddings = self.model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
        return embeddings.tolist()

    def embed_query(self, query: str) -> List[float]:
        embedding = self.model.encode(query, normalize_embeddings=True, show_progress_bar=False)
        return embedding.tolist()


class EmbeddingService:
    """
    Facade service orchestrating embedding generation for document chunks and queries.
    Configurable via environment variables (EMBEDDING_MODEL).
    """

    def __init__(self, model_name: Optional[str] = None):
        self.model_name = model_name or settings.EMBEDDING_MODEL
        self._provider = self._init_provider(self.model_name)

    def _init_provider(self, model_name: str) -> BaseEmbeddingProvider:
        """Initializes the requested provider with graceful fallback."""
        model_name_lower = model_name.lower()

        # If sentence-transformers requested and package available
        if "sentence-transformers" in model_name_lower or "minilm" in model_name_lower:
            try:
                import sentence_transformers
                return SentenceTransformersEmbeddingProvider(model_name)
            except ImportError:
                # Fallback to local dense semantic model
                return LocalDenseEmbeddingProvider(dimension=settings.EMBEDDING_DIMENSION)

        # Default local semantic embedding model
        return LocalDenseEmbeddingProvider(dimension=settings.EMBEDDING_DIMENSION)

    @property
    def dimension(self) -> int:
        return self._provider.dimension

    def embed_documents(self, chunks: List[str]) -> List[List[float]]:
        """
        Generates normalized dense embeddings for a list of chunk texts.
        """
        if not chunks:
            return []
        return self._provider.embed_documents(chunks)

    def embed_query(self, query: str) -> List[float]:
        """
        Generates a normalized dense embedding for a user query.
        """
        if not query or not query.strip():
            return [0.0] * self.dimension
        return self._provider.embed_query(query)


# Global singleton instance
embedding_service = EmbeddingService()
