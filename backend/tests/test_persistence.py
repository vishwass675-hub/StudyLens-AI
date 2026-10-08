"""
Unit and Integration Tests for StudyLens AI Persistence and Document Management Layer.
Tests SQLite metadata storage, document lifecycle, vector cleanup, conversation history,
automatic title generation, source provenance, and cross-document isolation.
"""

import io
import fitz
import pytest
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient

from backend.main import app
from backend.app.services.document_service import document_service
from backend.app.services.conversation_service import conversation_service
from backend.app.services.vector_store import vector_store
from backend.app.repositories.document_repository import document_repo
from backend.app.repositories.conversation_repository import conversation_repo
from backend.app.repositories.study_results_repository import study_results_repo


def create_sample_pdf(title: str, body: str) -> bytes:
    """Helper to create a valid minimal PDF in-memory."""
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 50), f"{title}\n\n{body}")
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


@pytest.fixture
def client():
    return TestClient(app)


# -----------------------------------------------------------------------------
# 1. DOCUMENT PERSISTENCE & LIFECYCLE TESTS
# -----------------------------------------------------------------------------
def test_document_creation_and_listing(client):
    """Test document creation, SQLite persistence, and listing with metadata."""
    pdf_bytes = create_sample_pdf("DBMS Unit 3", "Database normalization organizes tables to reduce redundancy.")
    res = client.post(
        "/api/documents/upload",
        files={"file": ("DBMS_Unit_3.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
    )
    assert res.status_code == 201
    data = res.json()
    doc_id = data["document_id"]
    assert data["filename"] == "DBMS_Unit_3.pdf"
    assert data["status"] == "ready"
    assert data["page_count"] == 1

    # Verify listing endpoint contains new document
    list_res = client.get("/api/documents")
    assert list_res.status_code == 200
    docs = list_res.json()["documents"]
    matched = [d for d in docs if d["document_id"] == doc_id]
    assert len(matched) == 1
    doc_meta = matched[0]
    assert doc_meta["filename"] == "DBMS_Unit_3.pdf"
    assert doc_meta["page_count"] == 1
    assert doc_meta["status"] == "ready"
    assert doc_meta["created_at"] is not None
    assert doc_meta["last_accessed_at"] is not None


def test_document_retrieval(client):
    """Test retrieving a single document's metadata."""
    pdf_bytes = create_sample_pdf("Operating Systems", "Process scheduling and virtual memory paging.")
    res = client.post(
        "/api/documents/upload",
        files={"file": ("Operating_Systems.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
    )
    doc_id = res.json()["document_id"]

    get_res = client.get(f"/api/documents/{doc_id}")
    assert get_res.status_code == 200
    detail = get_res.json()
    assert detail["document_id"] == doc_id
    assert detail["filename"] == "Operating_Systems.pdf"
    assert detail["status"] == "ready"


def test_document_safe_deletion_and_vector_cleanup(client):
    """Test that deleting a document cleans up SQLite records, vector embeddings, and cached data."""
    pdf_bytes = create_sample_pdf("Network Architecture", "OSI model consists of seven layers.")
    res = client.post(
        "/api/documents/upload",
        files={"file": ("Networks.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
    )
    doc_id = res.json()["document_id"]

    # Verify chunks exist in vector store
    initial_chunks_count = vector_store.count(doc_id)
    assert initial_chunks_count > 0

    # Create a conversation and cached study result for this document
    conv = conversation_service.create_conversation(document_id=doc_id, title="Networks Chat")
    conv_id = conv["id"]
    study_results_repo.save_result(doc_id, "summary", "test_hash", {"summary": "Overview"})

    # Perform DELETE
    del_res = client.delete(f"/api/documents/{doc_id}")
    assert del_res.status_code == 204

    # 1. Verify document is gone from API
    assert client.get(f"/api/documents/{doc_id}").status_code == 404

    # 2. Verify chunks are purged from vector store
    remaining_chunks_count = vector_store.count(doc_id)
    assert remaining_chunks_count == 0

    # 3. Verify conversation was cascaded/removed
    assert conversation_service.get_conversation(conv_id) is None

    # 4. Verify search on deleted document returns 404
    search_res = client.post(f"/api/documents/{doc_id}/search", json={"query": "OSI layers"})
    assert search_res.status_code == 404


# -----------------------------------------------------------------------------
# 2. CONVERSATION PERSISTENCE & HISTORY TESTS
# -----------------------------------------------------------------------------
def test_conversation_crud(client):
    """Test conversation creation, listing, renaming, and deletion."""
    pdf_bytes = create_sample_pdf("Algorithms", "Asymptotic analysis and Big-O notation.")
    res = client.post(
        "/api/documents/upload",
        files={"file": ("Algorithms.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
    )
    doc_id = res.json()["document_id"]

    # 1. Create conversation
    create_res = client.post(
        "/api/conversations",
        json={"document_id": doc_id, "title": "Complexity Discussion"},
    )
    assert create_res.status_code == 201
    conv = create_res.json()
    conv_id = conv["id"]
    assert conv["title"] == "Complexity Discussion"
    assert conv["document_id"] == doc_id
    assert conv["document_filename"] == "Algorithms.pdf"

    # 2. List conversations filtered by document_id
    list_res = client.get(f"/api/conversations?document_id={doc_id}")
    assert list_res.status_code == 200
    convs = list_res.json()["conversations"]
    assert any(c["id"] == conv_id for c in convs)

    # 3. Rename conversation
    patch_res = client.patch(
        f"/api/conversations/{conv_id}",
        json={"title": "Big-O Analysis Deep Dive"},
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["title"] == "Big-O Analysis Deep Dive"

    # 4. Delete conversation
    del_res = client.delete(f"/api/conversations/{conv_id}")
    assert del_res.status_code == 204
    assert client.get(f"/api/conversations/{conv_id}").status_code == 404


def test_automatic_chat_title_generation():
    """Verify automatic titling creates clean, concise titles from user questions."""
    assert conversation_service.generate_title("What is third normal form?") == "Third Normal Form"
    assert conversation_service.generate_title("Can you explain BCNF and 3NF?") == "Bcnf And 3Nf"
    assert conversation_service.generate_title("Why is database normalization needed?") == "Database Normalization Needed"
    assert conversation_service.generate_title("How to implement binary search?") == "Implement Binary Search"
    assert conversation_service.generate_title("Tell me about deadlock prevention") == "Deadlock Prevention"


# -----------------------------------------------------------------------------
# 3. MESSAGE PERSISTENCE & PROVENANCE
# -----------------------------------------------------------------------------
def test_chat_message_persistence_and_provenance(client):
    """Test full chat turn saves user message, assistant response, and retrieval sources."""
    pdf_bytes = create_sample_pdf(
        "Compiler Design",
        "Lexical analysis produces tokens from raw source characters."
    )
    res = client.post(
        "/api/documents/upload",
        files={"file": ("Compiler_Design.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
    )
    doc_id = res.json()["document_id"]

    mock_llm_response = {
        "answer": "Lexical analysis turns input characters into meaningful tokens.",
        "sources": [{"document": "Compiler_Design.pdf", "page": 1}],
    }

    with patch(
        "backend.app.services.llm_service.llm_tutor_service.generate_grounded_answer",
        new=AsyncMock(return_value=mock_llm_response),
    ):
        # 1. Ask question without passing conversation_id -> should auto-create conversation
        chat_res = client.post(
            "/api/chat",
            json={
                "document_id": doc_id,
                "message": "What is lexical analysis?",
                "mode": "simple",
            },
        )
        assert chat_res.status_code == 200
        chat_data = chat_res.json()
        conv_id = chat_data["conversation_id"]
        assert conv_id is not None
        assert chat_data["answer"] == mock_llm_response["answer"]
        assert len(chat_data["sources"]) == 1
        assert chat_data["sources"][0]["page"] == 1

        # 2. Check conversation auto-titled
        conv = conversation_service.get_conversation(conv_id)
        assert conv["title"] == "Lexical Analysis"

        # 3. Fetch stored messages
        msg_res = client.get(f"/api/conversations/{conv_id}/messages")
        assert msg_res.status_code == 200
        messages = msg_res.json()
        assert len(messages) == 2
        assert messages[0]["role"] == "user"
        assert messages[0]["content"] == "What is lexical analysis?"
        assert messages[1]["role"] == "assistant"
        assert messages[1]["content"] == mock_llm_response["answer"]
        assert len(messages[1]["sources"]) == 1
        assert messages[1]["sources"][0]["page"] == 1


# -----------------------------------------------------------------------------
# 4. RELATIONSHIP ENFORCEMENT & CROSS-DOCUMENT ISOLATION
# -----------------------------------------------------------------------------
def test_document_conversation_relationship_validation(client):
    """Verify that a conversation cannot be used with a mismatched document ID."""
    pdf_a = create_sample_pdf("Doc A", "Subject Alpha.")
    res_a = client.post(
        "/api/documents/upload",
        files={"file": ("DocA.pdf", io.BytesIO(pdf_a), "application/pdf")},
    )
    doc_a_id = res_a.json()["document_id"]

    pdf_b = create_sample_pdf("Doc B", "Subject Beta.")
    res_b = client.post(
        "/api/documents/upload",
        files={"file": ("DocB.pdf", io.BytesIO(pdf_b), "application/pdf")},
    )
    doc_b_id = res_b.json()["document_id"]

    # Create conversation for Doc A
    conv = conversation_service.create_conversation(document_id=doc_a_id, title="Doc A Chat")
    conv_id = conv["id"]

    # Try to chat with conv_id but specifying Doc B
    mismatch_res = client.post(
        "/api/chat",
        json={
            "document_id": doc_b_id,
            "conversation_id": conv_id,
            "message": "Hello from mismatched doc",
        },
    )
    assert mismatch_res.status_code == 400
    assert "does not belong" in mismatch_res.json()["detail"]


def test_cross_document_isolation(client):
    """Ensure vector retrieval strictly isolates document chunks."""
    pdf_physics = create_sample_pdf("Quantum Physics", "Schrodinger equation describes wave function.")
    res_phys = client.post(
        "/api/documents/upload",
        files={"file": ("Physics.pdf", io.BytesIO(pdf_physics), "application/pdf")},
    )
    phys_id = res_phys.json()["document_id"]

    pdf_history = create_sample_pdf("Ancient Rome", "Julius Caesar crossed the Rubicon.")
    res_hist = client.post(
        "/api/documents/upload",
        files={"file": ("Rome.pdf", io.BytesIO(pdf_history), "application/pdf")},
    )
    hist_id = res_hist.json()["document_id"]

    # Search Physics document for Caesar -> must return no results found
    search_phys = client.post(
        f"/api/documents/{phys_id}/search",
        json={"query": "Julius Caesar crossed the Rubicon"},
    )
    assert search_phys.status_code == 200
    data_phys = search_phys.json()
    assert all(r["document_id"] == phys_id for r in data_phys["results"])
    # Should not contain any Roman chunks
    assert not any("Rubicon" in r["text"] for r in data_phys["results"])

    # Search History document for Rubicon -> must return History chunks only
    search_hist = client.post(
        f"/api/documents/{hist_id}/search",
        json={"query": "Julius Caesar crossed the Rubicon"},
    )
    assert search_hist.status_code == 200
    data_hist = search_hist.json()
    assert all(r["document_id"] == hist_id for r in data_hist["results"])
    assert any("Rubicon" in r["text"] for r in data_hist["results"])
