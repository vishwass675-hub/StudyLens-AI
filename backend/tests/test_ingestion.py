"""
Unit and integration tests for the StudyLens AI PDF Ingestion Backend.
Tests:
1. Health check endpoint
2. Valid PDF upload and metadata response
3. Invalid file rejection (non-PDF extension and corrupt bytes)
4. PDF text extraction & cleaning verification
5. Page metadata preservation (1-indexed pages, word & char counts)
6. Chunk creation with page provenance and overlap
7. Empty/unreadable PDF error handling
"""

import io
import pytest
from backend.app.services.pdf_service import PDFService, InvalidPDFError, EmptyPDFError
from backend.app.services.chunking_service import ChunkingService
from backend.app.models.document import ExtractedPage
from backend.tests.conftest import generate_valid_pdf_bytes, generate_empty_pdf_bytes


def test_health_check(client):
    """Verifies that GET /api/health returns {'status': 'ok'}."""
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_valid_pdf_upload(client):
    """
    Test 1: Valid PDF upload.
    Verifies that a valid PDF can be uploaded, assigned a unique ID, and returns status 'ready'.
    """
    pdf_bytes = generate_valid_pdf_bytes()
    files = {"file": ("DBMS_Notes.pdf", io.BytesIO(pdf_bytes), "application/pdf")}

    response = client.post("/api/documents/upload", files=files)
    assert response.status_code == 201

    data = response.json()
    assert "document_id" in data
    assert data["document_id"].startswith("doc_")
    assert data["filename"] == "DBMS_Notes.pdf"
    assert data["page_count"] == 3
    assert data["status"] == "ready"


def test_invalid_file_extension_rejected(client):
    """
    Test 2a: Invalid file extension rejection.
    Uploading a .txt file should return 400 Bad Request.
    """
    files = {"file": ("notes.txt", io.BytesIO(b"Plain text notes"), "text/plain")}
    response = client.post("/api/documents/upload", files=files)
    assert response.status_code == 400
    assert "Only .pdf files are accepted" in response.json()["detail"]


def test_corrupt_pdf_content_rejected(client):
    """
    Test 2b: Fake PDF content rejection.
    Uploading a non-PDF file with a .pdf extension should return 400 Bad Request.
    """
    fake_bytes = b"This is plain text with no PDF magic bytes"
    files = {"file": ("fake_paper.pdf", io.BytesIO(fake_bytes), "application/pdf")}
    response = client.post("/api/documents/upload", files=files)
    assert response.status_code == 400
    assert "valid PDF" in response.json()["detail"]


def test_pdf_service_text_extraction():
    """
    Test 3: PDF text extraction & cleaning logic.
    Verifies that PyMuPDF extracts text page-by-page and normalizes whitespace.
    """
    pdf_bytes = generate_valid_pdf_bytes()
    service = PDFService()

    pages = service.extract_pages(
        document_id="test_doc_001",
        file_input=pdf_bytes,
        filename="test.pdf",
    )

    assert len(pages) == 3
    # Check page numbers
    assert [p.page for p in pages] == [1, 2, 3]

    # Check content of specific pages
    assert "Relational Model" in pages[0].text
    assert "Relational Algebra" in pages[1].text
    assert "ACID Properties" in pages[2].text

    # Check words & chars count
    assert pages[0].word_count > 20
    assert pages[0].char_count > 100

    # Test text cleaner directly
    dirty_text = "Database   systems\n\n\n\nsupport  transfor-\nmation."
    cleaned = service.clean_text(dirty_text)
    assert cleaned == "Database systems\n\nsupport transformation."


def test_page_metadata_preservation(client):
    """
    Test 4: Page metadata preservation via API.
    Verifies that GET /api/documents/{id}/pages returns pages with 1-indexed numbers and stats.
    """
    pdf_bytes = generate_valid_pdf_bytes()
    files = {"file": ("OS_Notes.pdf", io.BytesIO(pdf_bytes), "application/pdf")}

    upload_resp = client.post("/api/documents/upload", files=files)
    assert upload_resp.status_code == 201
    doc_id = upload_resp.json()["document_id"]

    pages_resp = client.get(f"/api/documents/{doc_id}/pages")
    assert pages_resp.status_code == 200
    pages = pages_resp.json()

    assert len(pages) == 3
    for idx, page_data in enumerate(pages, start=1):
        assert page_data["page"] == idx
        assert page_data["document_id"] == doc_id
        assert len(page_data["text"]) > 0
        assert page_data["char_count"] > 0
        assert page_data["word_count"] > 0


def test_chunking_service_creation():
    """
    Test 5a: Chunk creation unit test.
    Verifies that chunks maintain document ID, page numbers, and chunk IDs.
    """
    pages = [
        ExtractedPage(
            document_id="doc_xyz",
            page=1,
            text="First sentence of page one. Second sentence of page one. Third sentence discussing indexing.",
            char_count=93,
            word_count=14,
        ),
        ExtractedPage(
            document_id="doc_xyz",
            page=2,
            text="Page two introduces B+ Trees. B+ Trees have balanced search depth. Leaf nodes are linked sequentially.",
            char_count=103,
            word_count=16,
        ),
    ]

    chunker = ChunkingService(chunk_size=60, chunk_overlap=15, min_chunk_size=20)
    chunks = chunker.create_chunks("doc_xyz", pages)

    assert len(chunks) >= 2
    for c in chunks:
        assert c.document_id == "doc_xyz"
        assert c.page_number in [1, 2]
        assert c.chunk_id.startswith("doc_xyz_p")
        assert len(c.chunk_text) > 0


def test_chunks_endpoint(client):
    """
    Test 5b: Chunk creation via API.
    Verifies that GET /api/documents/{id}/chunks returns chunks with metadata.
    """
    pdf_bytes = generate_valid_pdf_bytes()
    files = {"file": ("Algorithms.pdf", io.BytesIO(pdf_bytes), "application/pdf")}

    upload_resp = client.post("/api/documents/upload", files=files)
    assert upload_resp.status_code == 201
    doc_id = upload_resp.json()["document_id"]

    chunks_resp = client.get(f"/api/documents/{doc_id}/chunks")
    assert chunks_resp.status_code == 200
    chunks = chunks_resp.json()

    assert len(chunks) >= 3
    # Check that chunks represent all 3 pages
    represented_pages = {c["page_number"] for c in chunks}
    assert 1 in represented_pages
    assert 2 in represented_pages
    assert 3 in represented_pages


def test_empty_pdf_handling(client):
    """
    Test 6: Empty/unreadable PDF error handling.
    Uploading a PDF with zero extractable text must return 422 Unprocessable Entity.
    """
    empty_bytes = generate_empty_pdf_bytes()
    files = {"file": ("empty_scan.pdf", io.BytesIO(empty_bytes), "application/pdf")}

    response = client.post("/api/documents/upload", files=files)
    assert response.status_code == 422
    assert "No extractable text found" in response.json()["detail"]


def test_document_status_lifecycle(client):
    """
    Test 7: Document status transitions and inspection.
    Verifies that GET /api/documents/{id} returns status 'ready' and complete metrics.
    """
    pdf_bytes = generate_valid_pdf_bytes()
    files = {"file": ("Compilers.pdf", io.BytesIO(pdf_bytes), "application/pdf")}

    upload_resp = client.post("/api/documents/upload", files=files)
    doc_id = upload_resp.json()["document_id"]

    detail_resp = client.get(f"/api/documents/{doc_id}")
    assert detail_resp.status_code == 200
    detail = detail_resp.json()

    assert detail["document_id"] == doc_id
    assert detail["status"] == "ready"
    assert detail["page_count"] == 3
    assert detail["total_words"] > 50
    assert detail["total_chunks"] >= 3
    assert detail["error_message"] is None
