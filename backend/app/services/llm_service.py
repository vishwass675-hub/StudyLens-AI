"""
Academic LLM Tutor Service for StudyLens AI.
Coordinates prompt engineering, tutor modes, retrieval injection,
and calls to Nemotron 3 Nano 30B Cloud via Ollama Cloud.
"""

from typing import List, Dict, Any, Optional
from backend.app.core.prompts import (
    SYSTEM_PROMPT,
    TutorMode,
    build_tutor_user_prompt,
)
from backend.app.services.ollama_client import OllamaCloudClient, ollama_client, OllamaCloudError
from backend.app.core.config import settings


class LLMTutorService:
    """
    Dedicated LLM service bridging retrieval results and Nemotron generation.
    Enforces strict grounding, tutor modes, and retrieval-based source extraction.
    """

    def __init__(self, client: Optional[OllamaCloudClient] = None):
        self.client = client or ollama_client

    def extract_sources(self, retrieved_chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Constructs the source list purely from actual retrieval metadata.
        Never trusts the LLM to generate page or document references.
        Returns unique (document, page) pairs preserving appearance order.
        """
        seen = set()
        sources = []
        for c in retrieved_chunks:
            doc_name = c.get("filename", "document.pdf")
            page_num = c.get("page", c.get("page_number", 1))
            key = (doc_name, page_num)
            if key not in seen:
                seen.add(key)
                sources.append({
                    "document": doc_name,
                    "page": int(page_num),
                })
        return sources

    async def generate_grounded_answer(
        self,
        question: str,
        retrieved_chunks: List[Dict[str, Any]],
        mode: TutorMode = TutorMode.SIMPLE,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        system_prompt: str = SYSTEM_PROMPT,
    ) -> Dict[str, Any]:
        """
        Generates a grounded academic tutor answer using Nemotron 3 Nano 30B Cloud.

        Args:
            question: The student's current question
            retrieved_chunks: Chunks from the vector retrieval stage
            mode: Tutor pedagogical mode (simple, detailed, exam, eli5)
            conversation_history: Prior chat messages for context
            system_prompt: System prompt defining grounding rules and persona

        Returns:
            Dict containing 'answer' and 'sources'
        """
        # Rule 10: If no relevant chunks were retrieved, do NOT ask the LLM to hallucinate
        if not retrieved_chunks:
            return {
                "answer": "I couldn't find enough information about that in the uploaded document.",
                "sources": [],
            }

        # 1. Build structured user prompt with isolated context sections
        user_prompt = build_tutor_user_prompt(
            question=question,
            retrieved_chunks=retrieved_chunks,
            mode=mode,
            conversation_history=conversation_history,
            max_turns=settings.MAX_CONVERSATION_TURNS,
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        # 2. Extract reliable sources from retrieval metadata
        sources = self.extract_sources(retrieved_chunks)

        # 3. Call Nemotron 3 Nano 30B Cloud
        try:
            answer = await self.client.generate_chat_completion(messages)
            return {
                "answer": answer.strip(),
                "sources": sources,
            }
        except OllamaCloudError as e:
            # Re-raise or return clean handled error
            raise e


# Global singleton instance
llm_tutor_service = LLMTutorService()
