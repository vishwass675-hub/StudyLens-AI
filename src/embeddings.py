"""
Embedding Service supporting Google Gemini (google-genai and google-generativeai), OpenAI, and Local Fallback embeddings.
"""

from typing import List, Optional
import os
import hashlib
import numpy as np


class EmbeddingService:
    """
    Generates dense vector embeddings for document chunks and user queries.
    Supports Google Gemini (default), OpenAI, and a local deterministic fallback.
    """

    def __init__(
        self,
        provider: str = "gemini",
        api_key: Optional[str] = None,
        model_name: Optional[str] = None,
    ):
        """
        Args:
            provider: 'gemini', 'openai', or 'local'
            api_key: API key string. If None, checks GEMINI_API_KEY / OPENAI_API_KEY in environment.
            model_name: Specific embedding model name override.
        """
        self.provider = provider.lower()
        self.api_key = (
            api_key
            or os.getenv("GEMINI_API_KEY")
            or os.getenv("GOOGLE_API_KEY")
            or os.getenv("OPENAI_API_KEY")
        )
        self.model_name = model_name

        if self.provider == "gemini":
            self.model_name = model_name or "text-embedding-004"
            # Try initializing google.genai or google.generativeai
            self._gemini_client = None
            resolved_key = (
                api_key
                or os.getenv("GEMINI_API_KEY")
                or os.getenv("GOOGLE_API_KEY")
            )
            if resolved_key:
                self.api_key = resolved_key
                try:
                    from google import genai
                    self._gemini_client = genai.Client(api_key=resolved_key)
                except Exception:
                    try:
                        import google.generativeai as genai_legacy
                        genai_legacy.configure(api_key=resolved_key)
                    except Exception:
                        pass

        elif self.provider == "openai":
            import openai
            resolved_key = api_key or os.getenv("OPENAI_API_KEY")
            if resolved_key:
                self.client = openai.OpenAI(api_key=resolved_key)
                self.api_key = resolved_key
            else:
                self.client = None
            self.model_name = model_name or "text-embedding-3-small"

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Generates embeddings for a list of document chunk texts."""
        if not texts:
            return []

        if self.provider == "gemini":
            return self._embed_gemini(texts, task_type="retrieval_document")
        elif self.provider == "openai":
            return self._embed_openai(texts)
        else:
            return self._embed_local_fallback(texts)

    def embed_query(self, query: str) -> List[float]:
        """Generates embedding for a user query."""
        if self.provider == "gemini":
            res = self._embed_gemini([query], task_type="retrieval_query")
            return res[0] if res else [0.0] * 768
        elif self.provider == "openai":
            res = self._embed_openai([query])
            return res[0] if res else [0.0] * 1536
        else:
            return self._embed_local_fallback([query])[0]

    def _embed_gemini(self, texts: List[str], task_type: str = "retrieval_document") -> List[List[float]]:
        if not self.api_key:
            raise ValueError(
                "Gemini API key is required. Set GEMINI_API_KEY in .env or provide it in the sidebar."
            )

        # 1. Try google.genai Client first
        if self._gemini_client is not None:
            try:
                embeddings = []
                batch_size = 50
                for i in range(0, len(texts), batch_size):
                    batch = texts[i : i + batch_size]
                    response = self._gemini_client.models.embed_content(
                        model=self.model_name,
                        contents=batch,
                    )
                    if hasattr(response, "embeddings") and response.embeddings:
                        for emb in response.embeddings:
                            embeddings.append(list(emb.values))
                    elif hasattr(response, "embedding") and response.embedding:
                        embeddings.append(list(response.embedding.values))
                if embeddings:
                    return embeddings
            except Exception as e:
                print(f"[StudyLens AI] google.genai embed_content fallback triggered: {e}")

        # 2. Try google.generativeai legacy client
        try:
            import google.generativeai as genai_legacy
            genai_legacy.configure(api_key=self.api_key)
            embeddings = []
            batch_size = 50
            for i in range(0, len(texts), batch_size):
                batch = texts[i : i + batch_size]
                try:
                    response = genai_legacy.embed_content(
                        model=f"models/{self.model_name.replace('models/', '')}",
                        content=batch,
                        task_type=task_type,
                    )
                    if "embedding" in response:
                        batch_embeds = response["embedding"]
                        if batch_embeds and isinstance(batch_embeds[0], (int, float)):
                            embeddings.append(batch_embeds)
                        else:
                            embeddings.extend(batch_embeds)
                except Exception:
                    for text in batch:
                        item_resp = genai_legacy.embed_content(
                            model=f"models/{self.model_name.replace('models/', '')}",
                            content=text,
                            task_type=task_type,
                        )
                        embeddings.append(item_resp["embedding"])
            return embeddings
        except Exception as e:
            raise RuntimeError(f"Gemini embedding failed: {str(e)}")

    def _embed_openai(self, texts: List[str]) -> List[List[float]]:
        if not self.client:
            raise ValueError(
                "OpenAI API key is required. Set OPENAI_API_KEY in .env or provide it in the sidebar."
            )

        embeddings = []
        batch_size = 100

        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            response = self.client.embeddings.create(
                model=self.model_name,
                input=batch,
            )
            embeddings.extend([item.embedding for item in response.data])

        return embeddings

    def _embed_local_fallback(self, texts: List[str], dim: int = 384) -> List[List[float]]:
        """
        Deterministic hash-based dense embedding fallback.
        Ensures local unit testing and dry runs succeed even without active network or API keys.
        """
        results = []
        for text in texts:
            words = text.lower().split()
            vec = np.zeros(dim, dtype=np.float32)
            if not words:
                results.append(vec.tolist())
                continue

            for word in words:
                h = int(hashlib.md5(word.encode("utf-8")).hexdigest(), 16)
                idx = h % dim
                sign = 1.0 if ((h >> 8) % 2 == 0) else -1.0
                vec[idx] += sign

            norm = np.linalg.norm(vec)
            if norm > 0:
                vec = vec / norm
            results.append(vec.tolist())

        return results
