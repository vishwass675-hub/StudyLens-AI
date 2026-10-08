"""
Unit and integration tests for the LLM generation and grounded AI tutor layer.
Covers:
1. System prompt grounding rules
2. Tutor mode formatting (SIMPLE, DETAILED, EXAM, ELI5)
3. Retrieved context structure and formatting
4. Source extraction purely from retrieval metadata
5. No-relevant-context behavior (controlled notice, zero sources)
6. Bounded conversation history
7. Ollama Cloud request construction & response mapping
8. End-to-end POST /api/chat with active document
9. Unrelated query behavior via POST /api/chat
10. Non-existent document 404 handling
"""

import io
import asyncio
import pytest
from unittest.mock import AsyncMock, patch

from backend.app.core.prompts import (
    SYSTEM_PROMPT,
    TutorMode,
    format_retrieved_context,
    format_conversation_history,
    build_tutor_user_prompt,
)
from backend.app.services.llm_service import LLMTutorService
from backend.app.services.ollama_client import OllamaCloudClient, OllamaCloudError
from backend.tests.conftest import generate_dbms_normalization_pdf_bytes


def test_1_system_prompt_grounding_rules():
    """Requirement 1: System prompt establishes grounding rules and truth source."""
    assert "You are StudyLens AI, an academic AI tutor." in SYSTEM_PROMPT
    assert "The uploaded document is the primary source of truth." in SYSTEM_PROMPT
    assert "Never invent missing information." in SYSTEM_PROMPT
    assert "Never invent page numbers or citations." in SYSTEM_PROMPT
    assert "explicitly say that the information was not found" in SYSTEM_PROMPT


def test_2_tutor_mode_instructions():
    """Requirement 2: Tutor modes (simple, detailed, exam, eli5) alter prompt instructions."""
    modes = [TutorMode.SIMPLE, TutorMode.DETAILED, TutorMode.EXAM, TutorMode.ELI5]
    dummy_chunk = [{"filename": "dbms.pdf", "page": 1, "text": "Sample content"}]

    prompts = [build_tutor_user_prompt("Explain keys", dummy_chunk, mode=m) for m in modes]

    # Ensure all mode instructions are distinct
    assert len(set(prompts)) == 4
    assert "TUTOR MODE: SIMPLE" in prompts[0]
    assert "TUTOR MODE: DETAILED" in prompts[1]
    assert "TUTOR MODE: EXAM PREPARATION" in prompts[2]
    assert "TUTOR MODE: ELI5" in prompts[3]


def test_3_retrieved_context_formatting():
    """Requirement 3: Retrieved chunks format follows standard Source blocks."""
    chunks = [
        {"filename": "DBMS_Notes.pdf", "page": 14, "text": "Normalization reduces redundancy."},
        {"filename": "DBMS_Notes.pdf", "page": 15, "text": "Third normal form (3NF)."},
    ]
    formatted = format_retrieved_context(chunks)

    assert "[Source 1]" in formatted
    assert "Document: DBMS_Notes.pdf" in formatted
    assert "Page: 14" in formatted
    assert "Normalization reduces redundancy." in formatted

    assert "[Source 2]" in formatted
    assert "Page: 15" in formatted
    assert "Third normal form (3NF)." in formatted


def test_4_source_extraction_from_metadata():
    """Requirement 4: Source list is constructed purely from retrieval metadata, never LLM."""
    service = LLMTutorService()
    chunks = [
        {"filename": "DBMS.pdf", "page": 14, "text": "Chunk 1"},
        {"filename": "DBMS.pdf", "page": 14, "text": "Chunk 2 from same page"},
        {"filename": "DBMS.pdf", "page": 15, "text": "Chunk 3"},
    ]
    sources = service.extract_sources(chunks)

    assert len(sources) == 2  # Deduplicated by (document, page)
    assert sources[0] == {"document": "DBMS.pdf", "page": 14}
    assert sources[1] == {"document": "DBMS.pdf", "page": 15}


def test_5_no_relevant_context_behavior():
    """Requirement 5: Controlled response when no relevant chunks are found."""
    mock_client = AsyncMock(spec=OllamaCloudClient)
    service = LLMTutorService(client=mock_client)

    result = asyncio.run(
        service.generate_grounded_answer(
            question="What is quantum gravity?",
            retrieved_chunks=[],  # No relevant context
        )
    )

    # Must NOT call the LLM to hallucinate
    mock_client.generate_chat_completion.assert_not_called()
    assert result["answer"] == "I couldn't find enough information about that in the uploaded document."
    assert result["sources"] == []


def test_6_conversation_context_bounding():
    """Requirement 6: Conversation history is bounded to max_turns."""
    history = [{"role": "user" if i % 2 == 0 else "assistant", "content": f"Message {i}"} for i in range(12)]
    formatted = format_conversation_history(history, max_turns=4)

    assert "Message 8" in formatted
    assert "Message 11" in formatted
    assert "Message 0" not in formatted
    assert "Message 5" not in formatted


def test_7_llm_service_with_mock_client():
    """Requirement 7: LLM service invokes Ollama Cloud client and returns answer + sources."""
    mock_client = AsyncMock(spec=OllamaCloudClient)
    mock_client.generate_chat_completion.return_value = (
        "Third Normal Form (3NF) requires a table to be in 2NF and have no transitive dependencies."
    )
    service = LLMTutorService(client=mock_client)

    chunks = [
        {"filename": "DBMS.pdf", "page": 14, "text": "3NF definition and transitive dependencies."},
    ]

    result = asyncio.run(
        service.generate_grounded_answer(
            question="What is 3NF?",
            retrieved_chunks=chunks,
            mode=TutorMode.EXAM,
        )
    )

    assert mock_client.generate_chat_completion.called
    assert "Third Normal Form" in result["answer"]
    assert len(result["sources"]) == 1
    assert result["sources"][0] == {"document": "DBMS.pdf", "page": 14}


def test_8_chat_api_endpoint_success(client):
    """Requirement 8: POST /api/chat end-to-end integration with active document."""
    # 1. Upload valid document
    pdf_bytes = generate_dbms_normalization_pdf_bytes()
    files = {"file": ("DBMS_Notes.pdf", io.BytesIO(pdf_bytes), "application/pdf")}
    upload_res = client.post("/api/documents/upload", files=files)
    assert upload_res.status_code == 201
    doc_id = upload_res.json()["document_id"]

    # 2. Mock Ollama client response during chat
    mock_answer = (
        "Normalization is the process of organizing relation schemas to eliminate data redundancy and anomalies."
    )

    with patch(
        "backend.app.services.llm_service.llm_tutor_service.client.generate_chat_completion",
        new_callable=AsyncMock,
    ) as mock_generate:
        mock_generate.return_value = mock_answer

        chat_payload = {
            "document_id": doc_id,
            "message": "Explain normalization and normal forms",
            "mode": "exam",
            "conversation": [],
            "top_k": 3,
        }

        resp = client.post("/api/chat", json=chat_payload)
        assert resp.status_code == 200

        data = resp.json()
        assert data["answer"] == mock_answer
        assert len(data["sources"]) >= 1

        # Page 2 has the normalization content
        pages = [s["page"] for s in data["sources"]]
        assert 2 in pages
        assert data["sources"][0]["document"] == "DBMS_Notes.pdf"


def test_9_chat_api_no_relevant_context(client):
    """Requirement 9: POST /api/chat when asking completely unrelated question."""
    pdf_bytes = generate_dbms_normalization_pdf_bytes()
    files = {"file": ("DBMS.pdf", io.BytesIO(pdf_bytes), "application/pdf")}
    upload_res = client.post("/api/documents/upload", files=files)
    doc_id = upload_res.json()["document_id"]

    # Ask completely unrelated botany question with reasonable threshold
    chat_payload = {
        "document_id": doc_id,
        "message": "Photosynthesis chlorophyll thylakoid light reactions botany biology",
        "mode": "simple",
        "similarity_threshold": 0.35,
    }

    resp = client.post("/api/chat", json=chat_payload)
    assert resp.status_code == 200
    data = resp.json()

    assert "I couldn't find enough information about that in the uploaded document." in data["answer"]
    assert data["sources"] == []


def test_10_chat_api_invalid_document_id(client):
    """Requirement 10: POST /api/chat returns 404 for non-existent document ID."""
    chat_payload = {
        "document_id": "doc_nonexistent_999",
        "message": "Explain normalization",
        "mode": "simple",
    }
    resp = client.post("/api/chat", json=chat_payload)
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()
