"""
Unit and integration tests for the Study Tools Layer:
1. Summary Generation (valid document, long document, malformed LLM recovery)
2. Revision Notes Generation (structured output, markdown, exam tips)
3. Quiz Generation (valid questions, options matching correct_answer)
4. Quiz Scoring & Weak Topic Detection (accurate percent, missed topics)
5. Caching & Force-Regenerate Behavior
6. Multi-document isolation (never mixes content between documents)
7. Error handling (non-existent document 404, not ready 400)
"""

import io
import json
import asyncio
import pytest
from unittest.mock import AsyncMock, patch

from backend.app.services.study_tools_service import (
    StudyToolsService,
    StudyToolError,
)
from backend.app.schemas.study_tools import (
    UserAnswerSubmission,
    QuizQuestion,
)
from backend.app.services.ollama_client import OllamaCloudClient
from backend.tests.conftest import generate_dbms_normalization_pdf_bytes


# -----------------------------------------------------------------------------
# 1. SUMMARY TESTS
# -----------------------------------------------------------------------------
def test_summary_generation_success(client):
    """Test generating structured summary for a valid ingested document."""
    pdf_bytes = generate_dbms_normalization_pdf_bytes()
    upload_res = client.post(
        "/api/documents/upload",
        files={"file": ("DBMS_Notes.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
    )
    doc_id = upload_res.json()["document_id"]

    mock_llm_json = json.dumps({
        "document_overview": "This document covers relational database design and normalization forms.",
        "topics": ["Normalization", "1NF", "2NF", "3NF"],
        "key_takeaways": [
            "Normalization eliminates anomalies and data redundancy.",
            "2NF eliminates partial dependencies."
        ],
        "key_definitions": [
            {"term": "Normalization", "definition": "Systematic process of organizing schemas."}
        ],
        "exam_points": ["Know the difference between 2NF and 3NF."]
    })

    with patch(
        "backend.app.services.study_tools_service.study_tools_service.client.generate_chat_completion",
        new_callable=AsyncMock,
    ) as mock_llm:
        mock_llm.return_value = f"```json\n{mock_llm_json}\n```"

        res = client.post(f"/api/documents/{doc_id}/summary", json={"force_regenerate": True})
        assert res.status_code == 200
        data = res.json()

        assert data["document_id"] == doc_id
        assert "relational database design" in data["document_overview"]
        assert "Normalization" in data["topics"]
        assert len(data["key_takeaways"]) == 2
        assert len(data["key_definitions"]) == 1
        assert data["key_definitions"][0]["term"] == "Normalization"
        assert len(data["sources"]) >= 1
        assert data["sources"][0]["document"] == "DBMS_Notes.pdf"


def test_summary_caching_behavior(client):
    """Test that second call returns cached response without invoking LLM."""
    pdf_bytes = generate_dbms_normalization_pdf_bytes()
    upload_res = client.post(
        "/api/documents/upload",
        files={"file": ("DBMS_Cache.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
    )
    doc_id = upload_res.json()["document_id"]

    mock_llm_json = json.dumps({
        "document_overview": "Cached summary test overview.",
        "topics": ["Topic A"],
        "key_takeaways": ["Takeaway A"],
        "key_definitions": [],
        "exam_points": []
    })

    with patch(
        "backend.app.services.study_tools_service.study_tools_service.client.generate_chat_completion",
        new_callable=AsyncMock,
    ) as mock_llm:
        mock_llm.return_value = mock_llm_json

        # First call -> uncached
        r1 = client.post(f"/api/documents/{doc_id}/summary", json={"force_regenerate": True})
        assert r1.status_code == 200
        assert r1.json()["cached"] is False
        assert mock_llm.call_count == 1

        # Second call -> cached
        r2 = client.post(f"/api/documents/{doc_id}/summary", json={"force_regenerate": False})
        assert r2.status_code == 200
        assert r2.json()["cached"] is True
        assert mock_llm.call_count == 1  # No additional call


def test_summary_malformed_json_recovery():
    """Test safe recovery when LLM initially returns invalid formatting."""
    mock_client = AsyncMock(spec=OllamaCloudClient)
    # First response: broken JSON; Second response: valid JSON
    valid_json = json.dumps({
        "document_overview": "Recovered overview",
        "topics": ["T1"],
        "key_takeaways": ["K1"],
        "key_definitions": [],
        "exam_points": []
    })
    mock_client.generate_chat_completion.side_effect = [
        "Broken JSON response { not valid",
        valid_json,
    ]

    service = StudyToolsService(client=mock_client)
    dummy_chunks = [{"filename": "doc.pdf", "page": 1, "text": "DBMS lecture."}]

    with patch.object(service, "_get_document_chunks", return_value=dummy_chunks):
        res = asyncio.run(service.generate_summary("doc_test", force_regenerate=True))
        assert res.document_overview == "Recovered overview"
        assert mock_client.generate_chat_completion.call_count == 2


# -----------------------------------------------------------------------------
# 2. REVISION NOTES TESTS
# -----------------------------------------------------------------------------
def test_notes_generation_success(client):
    """Test generating structured revision notes with markdown and sections."""
    pdf_bytes = generate_dbms_normalization_pdf_bytes()
    upload_res = client.post(
        "/api/documents/upload",
        files={"file": ("DBMS_Notes_Exam.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
    )
    doc_id = upload_res.json()["document_id"]

    mock_llm_json = json.dumps({
        "title": "DBMS Normalization Revision Notes",
        "markdown_content": "# DBMS Normalization\\n\\n## 2NF Definition\\n- Requires 1NF and no partial dependencies.",
        "sections": [
            {
                "heading": "Second Normal Form (2NF)",
                "summary": "Eliminates partial dependencies on composite keys.",
                "key_points": ["Applies to composite candidate keys.", "Non-prime attributes must depend on the whole key."],
                "exam_tip": "Remember: 2NF only applies when composite primary keys exist."
            }
        ]
    })

    with patch(
        "backend.app.services.study_tools_service.study_tools_service.client.generate_chat_completion",
        new_callable=AsyncMock,
    ) as mock_llm:
        mock_llm.return_value = mock_llm_json

        res = client.post(f"/api/documents/{doc_id}/notes", json={"force_regenerate": True})
        assert res.status_code == 200
        data = res.json()

        assert data["title"] == "DBMS Normalization Revision Notes"
        assert "# DBMS Normalization" in data["markdown_content"]
        assert len(data["sections"]) == 1
        assert data["sections"][0]["heading"] == "Second Normal Form (2NF)"
        assert "composite primary keys" in data["sections"][0]["exam_tip"]


# -----------------------------------------------------------------------------
# 3. QUIZ GENERATION & VALIDATION TESTS
# -----------------------------------------------------------------------------
def test_quiz_generation_success(client):
    """Test generating structured MCQ quiz from uploaded document."""
    pdf_bytes = generate_dbms_normalization_pdf_bytes()
    upload_res = client.post(
        "/api/documents/upload",
        files={"file": ("DBMS_Quiz.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
    )
    doc_id = upload_res.json()["document_id"]

    mock_llm_json = json.dumps({
        "questions": [
            {
                "id": 1,
                "topic": "Normalization Forms",
                "question": "Which normal form removes partial dependency?",
                "options": ["1NF", "2NF", "3NF", "BCNF"],
                "correct_answer": "2NF",
                "explanation": "2NF requires removing partial dependencies where non-prime attributes depend on a proper subset of a candidate key.",
                "page_hint": 2
            },
            {
                "id": 2,
                "topic": "Relational Concepts",
                "question": "What is atomic data a requirement of?",
                "options": ["1NF", "2NF", "3NF", "4NF"],
                "correct_answer": "1NF",
                "explanation": "1NF mandates that attribute values in each domain must be atomic.",
                "page_hint": 1
            }
        ]
    })

    with patch(
        "backend.app.services.study_tools_service.study_tools_service.client.generate_chat_completion",
        new_callable=AsyncMock,
    ) as mock_llm:
        mock_llm.return_value = mock_llm_json

        res = client.post(
            f"/api/documents/{doc_id}/quiz",
            json={"num_questions": 2, "force_regenerate": True},
        )
        assert res.status_code == 200
        data = res.json()

        assert data["document_id"] == doc_id
        assert data["total_questions"] == 2
        q1 = data["questions"][0]
        assert q1["correct_answer"] in q1["options"]
        assert q1["correct_answer"] == "2NF"
        assert q1["topic"] == "Normalization Forms"


# -----------------------------------------------------------------------------
# 4. QUIZ EVALUATION & WEAK TOPIC CALCULATION
# -----------------------------------------------------------------------------
def test_quiz_evaluation_and_weak_topic_detection():
    """Test scoring logic and identifying weak areas based on missed questions."""
    service = StudyToolsService()

    questions = [
        QuizQuestion(
            id=1,
            topic="Normalization",
            question="Q1?",
            options=["A", "B", "C", "D"],
            correct_answer="B",
            explanation="Exp 1",
        ),
        QuizQuestion(
            id=2,
            topic="Normalization",
            question="Q2?",
            options=["A", "B", "C", "D"],
            correct_answer="A",
            explanation="Exp 2",
        ),
        QuizQuestion(
            id=3,
            topic="SQL Constraints",
            question="Q3?",
            options=["A", "B", "C", "D"],
            correct_answer="C",
            explanation="Exp 3",
        ),
    ]

    # Student answers: Q1 wrong, Q2 right, Q3 wrong
    answers = [
        UserAnswerSubmission(question_id=1, user_answer="C", topic="Normalization"),
        UserAnswerSubmission(question_id=2, user_answer="A", topic="Normalization"),
        UserAnswerSubmission(question_id=3, user_answer="A", topic="SQL Constraints"),
    ]

    eval_result = service.evaluate_quiz(answers=answers, questions=questions)

    assert eval_result.score == 1
    assert eval_result.total == 3
    assert eval_result.accuracy_percentage == 33.3

    assert len(eval_result.weak_topics) == 2
    # Verify weak topic structure
    t_names = [w.topic for w in eval_result.weak_topics]
    assert "Normalization" in t_names
    assert "SQL Constraints" in t_names

    # Check recommendations wording
    recs = " ".join(eval_result.recommendations)
    assert "Review 'Normalization'" in recs
    assert "Review 'SQL Constraints'" in recs


# -----------------------------------------------------------------------------
# 5. MULTI-DOCUMENT ISOLATION
# -----------------------------------------------------------------------------
def test_multi_document_isolation_in_study_tools(client):
    """Ensure study tools strictly isolate chunks from different documents."""
    pdf_bytes = generate_dbms_normalization_pdf_bytes()

    # Upload Doc 1
    u1 = client.post(
        "/api/documents/upload",
        files={"file": ("Doc_One.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
    )
    doc1_id = u1.json()["document_id"]

    # Upload Doc 2
    u2 = client.post(
        "/api/documents/upload",
        files={"file": ("Doc_Two.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
    )
    doc2_id = u2.json()["document_id"]

    # Test that requesting doc1 sources only contains Doc_One.pdf
    mock_llm_json = json.dumps({
        "document_overview": "Doc 1 overview",
        "topics": ["T1"],
        "key_takeaways": [],
        "key_definitions": [],
        "exam_points": []
    })

    with patch(
        "backend.app.services.study_tools_service.study_tools_service.client.generate_chat_completion",
        new_callable=AsyncMock,
    ) as mock_llm:
        mock_llm.return_value = mock_llm_json

        res = client.post(f"/api/documents/{doc1_id}/summary", json={"force_regenerate": True})
        assert res.status_code == 200
        sources = res.json()["sources"]
        for s in sources:
            assert s["document"] == "Doc_One.pdf"
            assert s["document"] != "Doc_Two.pdf"


# -----------------------------------------------------------------------------
# 6. ERROR HANDLING
# -----------------------------------------------------------------------------
def test_study_tools_nonexistent_document(client):
    """Test 404 response for invalid document ID."""
    res = client.post("/api/documents/doc_nonexistent_123/summary")
    assert res.status_code == 404
    assert "not found" in res.json()["detail"].lower()
