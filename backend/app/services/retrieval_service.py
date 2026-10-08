"""
Semantic retrieval service for StudyLens AI.
Embeds user queries, searches the persistent vector store with document isolation,
ranks chunks by cosine similarity, and enforces relevance thresholds.
"""

from typing import List, Optional, Dict, Any
from dataclasses import dataclass

from backend.app.services.embedding_service import embedding_service
from backend.app.services.vector_store import vector_store, VectorSearchResult
from backend.app.core.config import settings


@dataclass
class RetrievalResponseData:
    """Encapsulates semantic retrieval results."""
    document_id: str
    query: str
    relevant_found: bool
    results_count: int
    results: List[Dict[str, Any]]
    message: Optional[str] = None


class RetrievalService:
    """
    Coordinates semantic search, document filtering, and threshold validation.
    """

    def __init__(self):
        self.embedding_service = embedding_service
        self.vector_store = vector_store

    def retrieve_relevant_chunks(
        self,
        document_id: str,
        query: str,
        top_k: Optional[int] = None,
        similarity_threshold: Optional[float] = None,
    ) -> RetrievalResponseData:
        """
        Executes semantic retrieval for a document:
        1. Embeds the user query.
        2. Retrieves top-k chunks from vector store filtered by document_id.
        3. Applies similarity threshold filtering.
        4. Returns structured results.
        """
        k = top_k or settings.DEFAULT_TOP_K
        threshold = (
            similarity_threshold
            if similarity_threshold is not None
            else settings.SIMILARITY_THRESHOLD
        )

        # 1. Embed query
        q_emb = self.embedding_service.embed_query(query)

        # 2. Search vector store
        raw_results: List[VectorSearchResult] = self.vector_store.search(
            document_id=document_id,
            query_embedding=q_emb,
            top_k=k,
        )

        if not raw_results:
            return RetrievalResponseData(
                document_id=document_id,
                query=query,
                relevant_found=False,
                results_count=0,
                results=[],
                message="No chunks found for this document in the vector store.",
            )

        # 3. Apply relevance threshold
        filtered_results = [r for r in raw_results if r.score >= threshold]

        # Graceful fallback: for broad queries (e.g. "what is this about?", "summarize this")
        # or compact documents where top chunks exist, never starve the LLM tutor of document context
        if not filtered_results and raw_results:
            filtered_results = raw_results[:min(k, 3)]

        results_data = [r.to_dict() for r in filtered_results]

        return RetrievalResponseData(
            document_id=document_id,
            query=query,
            relevant_found=bool(results_data),
            results_count=len(results_data),
            results=results_data,
        )


# Global singleton instance
retrieval_service = RetrievalService()
