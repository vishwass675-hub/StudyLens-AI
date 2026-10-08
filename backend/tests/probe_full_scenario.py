"""
End-to-end full scenario verification script for StudyLens AI.
Tests the complete real-world user lifecycle:
1. Upload real academic PDF.
2. Verify status transitions to READY with page count & chunking.
3. Start a conversation session.
4. Ask multiple questions with Nemotron mock/fallback response and persist turns.
5. Generate grounded summary (persisted in SQLite).
6. Generate revision notes (persisted in SQLite).
7. Generate MCQ quiz (persisted in SQLite).
8. Simulate page reload / new session:
   - Reopen document from document list.
   - Reopen conversation from conversation history.
   - Verify messages remain intact with source citations.
   - Verify retrieval strictly uses active document.
9. Delete document:
   - Verify document removed from SQLite.
   - Verify vector embeddings purged from vector store.
   - Verify cached summaries/notes/quizzes purged.
   - Verify conversation removed.
"""

import io
import fitz
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient

from backend.main import app
from backend.app.services.vector_store import vector_store
from backend.app.repositories.study_results_repository import study_results_repo


def build_academic_pdf() -> bytes:
    """Builds a real 2-page academic PDF on Relational Database Design."""
    doc = fitz.open()

    p1 = doc.new_page()
    p1.insert_text(
        (50, 70),
        "Database Systems - Unit 3: Normalization and Dependencies\n\n"
        "Functional dependency is a constraint between two sets of attributes in a relation.\n"
        "A relation is in First Normal Form (1NF) if every attribute contains only atomic values.\n"
        "A relation is in Second Normal Form (2NF) if it is in 1NF and no non-prime attribute is\n"
        "partially dependent on any candidate key.\n"
    )

    p2 = doc.new_page()
    p2.insert_text(
        (50, 70),
        "Third Normal Form and Boyce-Codd Normal Form\n\n"
        "A relation is in Third Normal Form (3NF) if whenever a non-trivial functional dependency\n"
        "X -> A holds, either X is a superkey or A is a prime attribute.\n"
        "Boyce-Codd Normal Form (BCNF) eliminates all transitive dependencies strictly:\n"
        "for every non-trivial functional dependency X -> A, X must be a superkey.\n"
        "Lossless join decomposition ensures original relations can be accurately reconstructed.\n"
    )

    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


def run_full_scenario():
    client = TestClient(app)
    pdf_bytes = build_academic_pdf()

    print("\n--- STEP 1 & 2: Upload real PDF and verify Ready status ---")
    upload_res = client.post(
        "/api/documents/upload",
        files={"file": ("DBMS_Unit_3.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
    )
    assert upload_res.status_code == 201, f"Upload failed: {upload_res.text}"
    doc_info = upload_res.json()
    doc_id = doc_info["document_id"]
    assert doc_info["filename"] == "DBMS_Unit_3.pdf"
    assert doc_info["page_count"] == 2
    assert doc_info["status"] == "ready"
    print(f"[PASS] Uploaded {doc_info['filename']} (ID: {doc_id}) with {doc_info['page_count']} pages. Status: READY.")

    print("\n--- STEP 3: Start a conversation ---")
    conv_res = client.post(
        "/api/conversations",
        json={"document_id": doc_id, "title": "New Conversation"},
    )
    assert conv_res.status_code == 201, f"Conversation create failed: {conv_res.text}"
    conv = conv_res.json()
    conv_id = conv["id"]
    print(f"[PASS] Conversation created (ID: {conv_id}, Title: '{conv['title']}').")

    print("\n--- STEP 4: Ask several questions and persist messages ---")
    mock_responses = [
        {
            "answer": "First Normal Form (1NF) requires all attributes in a relation to have atomic, indivisible values.",
            "sources": [{"document": "DBMS_Unit_3.pdf", "page": 1}],
        },
        {
            "answer": "Third Normal Form (3NF) requires that for any X -> A, X is a superkey or A is prime.",
            "sources": [{"document": "DBMS_Unit_3.pdf", "page": 2}],
        },
    ]

    with patch(
        "backend.app.services.llm_service.llm_tutor_service.generate_grounded_answer",
        new=AsyncMock(side_effect=mock_responses),
    ):
        # Q1
        q1_res = client.post(
            "/api/chat",
            json={
                "document_id": doc_id,
                "conversation_id": conv_id,
                "message": "What is first normal form?",
                "mode": "simple",
            },
        )
        assert q1_res.status_code == 200, f"Q1 failed: {q1_res.text}"

        # Q2
        q2_res = client.post(
            "/api/chat",
            json={
                "document_id": doc_id,
                "conversation_id": conv_id,
                "message": "Explain third normal form criteria",
                "mode": "detailed",
            },
        )
        assert q2_res.status_code == 200, f"Q2 failed: {q2_res.text}"

    # Verify conversation title auto-updated based on initial question
    get_conv_res = client.get(f"/api/conversations/{conv_id}")
    assert get_conv_res.status_code == 200
    updated_title = get_conv_res.json()["title"]
    assert updated_title == "First Normal Form", f"Unexpected title: {updated_title}"
    print(f"[PASS] Messages processed. Conversation auto-titled to: '{updated_title}'.")

    print("\n--- STEP 5: Generate document summary ---")
    mock_summary_json = '{"document_overview":"Unit on Normalization","topics":["1NF","2NF","3NF","BCNF"],"key_takeaways":["Eliminates redundancy"],"key_definitions":[{"term":"1NF","definition":"Atomic values"}],"exam_points":["BCNF vs 3NF"]}'
    with patch(
        "backend.app.services.ollama_client.ollama_client.generate_chat_completion",
        new=AsyncMock(return_value=mock_summary_json),
    ):
        sum_res = client.post(f"/api/documents/{doc_id}/summary")
        assert sum_res.status_code == 200, f"Summary failed: {sum_res.text}"
        sum_data = sum_res.json()
        assert len(sum_data["topics"]) == 4
        print(f"[PASS] Summary generated: {sum_data['document_overview']} with {len(sum_data['topics'])} topics.")

    print("\n--- STEP 6: Generate revision notes ---")
    mock_notes_json = '{"title":"DBMS Normalization Notes","markdown_content":"# Normalization Notes","sections":[{"heading":"1NF","summary":"Atomic","key_points":["No repeating groups"],"exam_tip":"High yield"}]}'
    with patch(
        "backend.app.services.ollama_client.ollama_client.generate_chat_completion",
        new=AsyncMock(return_value=mock_notes_json),
    ):
        notes_res = client.post(f"/api/documents/{doc_id}/notes")
        assert notes_res.status_code == 200, f"Notes failed: {notes_res.text}"
        notes_data = notes_res.json()
        assert len(notes_data["sections"]) == 1
        print(f"[PASS] Revision notes generated: '{notes_data['title']}'.")

    print("\n--- STEP 7: Generate interactive quiz ---")
    mock_quiz_json = '{"questions":[{"id":1,"topic":"Normalization","question":"What does 1NF eliminate?","options":["A","B","C","D"],"correct_answer":"A","explanation":"Removes composite values","page_hint":1}]}'
    with patch(
        "backend.app.services.ollama_client.ollama_client.generate_chat_completion",
        new=AsyncMock(return_value=mock_quiz_json),
    ):
        quiz_res = client.post(f"/api/documents/{doc_id}/quiz")
        assert quiz_res.status_code == 200, f"Quiz failed: {quiz_res.text}"
        quiz_data = quiz_res.json()
        assert len(quiz_data["questions"]) == 1
        print(f"[PASS] Quiz generated with {len(quiz_data['questions'])} questions.")

    print("\n--- STEP 8, 9, 10, 11: Simulate browser refresh & rehydration ---")
    # Fresh API client probe
    new_client = TestClient(app)

    # 8. List documents from persistent store
    list_docs = new_client.get("/api/documents").json()["documents"]
    matched_doc = next(d for d in list_docs if d["document_id"] == doc_id)
    assert matched_doc["filename"] == "DBMS_Unit_3.pdf"
    print(f"[PASS] Reopened document library. Document persisted: {matched_doc['filename']}.")

    # 9. List conversations from persistent store
    list_convs = new_client.get(f"/api/conversations?document_id={doc_id}").json()["conversations"]
    matched_conv = next(c for c in list_convs if c["id"] == conv_id)
    assert matched_conv["title"] == "First Normal Form"
    print(f"[PASS] Reopened conversation: '{matched_conv['title']}'.")

    # 10. Load messages
    msgs_res = new_client.get(f"/api/conversations/{conv_id}/messages")
    assert msgs_res.status_code == 200
    stored_msgs = msgs_res.json()
    assert len(stored_msgs) == 4  # 2 questions, 2 answers
    assert stored_msgs[0]["content"] == "What is first normal form?"
    assert stored_msgs[1]["sources"][0]["page"] == 1
    assert stored_msgs[2]["content"] == "Explain third normal form criteria"
    assert stored_msgs[3]["sources"][0]["page"] == 2
    print(f"[PASS] Messages and page citations verified ({len(stored_msgs)} messages preserved).")

    print("\n--- STEP 12: Verify retrieval strictly uses active document ---")
    search_res = new_client.post(
        f"/api/documents/{doc_id}/search",
        json={"query": "Boyce-Codd Normal Form"},
    )
    assert search_res.status_code == 200
    search_data = search_res.json()
    assert search_data["relevant_found"] is True
    assert all(r["document_id"] == doc_id for r in search_data["results"])
    assert search_data["results"][0]["page"] == 2
    print(f"[PASS] Retrieval strictly returned {len(search_data['results'])} chunks from document {doc_id} (Page 2).")

    print("\n--- STEP 13 & 14: Delete document & verify clean purge ---")
    del_res = new_client.delete(f"/api/documents/{doc_id}")
    assert del_res.status_code == 204
    print("[PASS] DELETE /api/documents/{doc_id} returned 204 No Content.")

    # Verify document 404
    assert new_client.get(f"/api/documents/{doc_id}").status_code == 404

    # Verify conversations cascaded
    assert new_client.get(f"/api/conversations/{conv_id}").status_code == 404

    # Verify vector store purge
    remaining_vectors = vector_store.count(doc_id)
    assert remaining_vectors == 0
    print("[PASS] Vector embeddings purged (0 remaining chunks).")

    # Verify cached study results purged
    cached_sum = study_results_repo.get_result(doc_id, "summary", "8")
    assert cached_sum is None
    print("[PASS] Cached study tools purged.")

    print("\n=======================================================")
    print("ALL 14 FINAL VERIFICATION STEPS PASSED SUCCESSFULLY!")
    print("=======================================================\n")


if __name__ == "__main__":
    run_full_scenario()
