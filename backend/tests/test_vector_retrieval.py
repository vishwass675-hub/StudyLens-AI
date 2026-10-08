"""
Comprehensive test suite for the Embedding and Vector Retrieval layer in StudyLens AI.
Covers all 10 requirements:
1. Embedding generation
2. Query embedding
3. Vector insertion
4. Vector persistence across instances
5. Semantic retrieval
6. document_id filtering
7. Top-K behavior
8. Similarity threshold behavior
9. Correct page metadata
10. Multi-document isolation (zero cross-document contamination)
"""

import io
import pytest
import numpy as np
from pathlib import Path

from backend.app.services.embedding_service import EmbeddingService
from backend.app.services.vector_store import LocalVectorStore
from backend.app.services.retrieval_service import RetrievalService
from backend.app.models.document import DocumentChunk
from backend.tests.conftest import (
    generate_dbms_normalization_pdf_bytes,
    generate_networks_pdf_bytes,
)


def test_1_embedding_generation():
    """Requirement 1: Generates normalized vector embeddings for document chunks."""
    service = EmbeddingService()
    chunks = [
        "First Normal Form requires all attribute domains to be atomic.",
        "Boyce-Codd Normal Form requires every determinant to be a superkey.",
    ]
    embeddings = service.embed_documents(chunks)

    assert len(embeddings) == 2
    assert len(embeddings[0]) == service.dimension
    assert len(embeddings[1]) == service.dimension

    # Verify L2 normalization: norm should equal 1.0
    norm_0 = np.linalg.norm(np.array(embeddings[0]))
    norm_1 = np.linalg.norm(np.array(embeddings[1]))
    assert abs(norm_0 - 1.0) < 1e-4
    assert abs(norm_1 - 1.0) < 1e-4


def test_2_query_embedding():
    """Requirement 2: Generates a normalized vector embedding for user query."""
    service = EmbeddingService()
    query = "What is database normalization and 3NF?"
    q_emb = service.embed_query(query)

    assert len(q_emb) == service.dimension
    q_norm = np.linalg.norm(np.array(q_emb))
    assert abs(q_norm - 1.0) < 1e-4


def test_3_vector_insertion(tmp_path):
    """Requirement 3: Inserts vector embeddings with metadata into local vector store."""
    db_file = tmp_path / "test_vec.db"
    store = LocalVectorStore(db_path=db_file)

    chunks = [
        DocumentChunk(
            document_id="doc_test_1",
            chunk_id="chunk_01",
            page_number=2,
            chunk_index=0,
            chunk_text="Normalization eliminates redundancy.",
            char_count=36,
            word_count=4,
        )
    ]
    emb = [[0.1] * 384]

    inserted = store.insert_chunks(
        document_id="doc_test_1",
        filename="dbms.pdf",
        chunks=chunks,
        embeddings=emb,
    )
    assert inserted == 1
    assert store.count("doc_test_1") == 1
    assert store.has_document("doc_test_1") is True


def test_4_vector_persistence(tmp_path):
    """Requirement 4: Vector store persists across new instances/restarts."""
    db_file = tmp_path / "persistent_vectors.db"

    # Instance 1: write vectors
    store_1 = LocalVectorStore(db_path=db_file)
    chunks = [
        DocumentChunk(
            document_id="doc_persist",
            chunk_id="c_persist_01",
            page_number=14,
            chunk_index=0,
            chunk_text="Persistent storage test chunk.",
            char_count=30,
            word_count=4,
        )
    ]
    store_1.insert_chunks(
        document_id="doc_persist",
        filename="persistent.pdf",
        chunks=chunks,
        embeddings=[[0.05] * 384],
    )
    assert store_1.count("doc_persist") == 1

    # Instance 2: read from same path
    store_2 = LocalVectorStore(db_path=db_file)
    assert store_2.has_document("doc_persist") is True
    assert store_2.count("doc_persist") == 1

    results = store_2.search("doc_persist", query_embedding=[0.05] * 384, top_k=1)
    assert len(results) == 1
    assert results[0].chunk_id == "c_persist_01"
    assert results[0].page == 14
    assert results[0].filename == "persistent.pdf"


def test_5_semantic_retrieval(client):
    """
    Requirement 5: End-to-end semantic retrieval.
    Uploads a DBMS PDF and searches for 'Explain normalization'.
    Verifies that the Normalization chunk (from Page 2) ranks #1 with high similarity.
    """
    pdf_bytes = generate_dbms_normalization_pdf_bytes()
    files = {"file": ("DBMS_Normalization.pdf", io.BytesIO(pdf_bytes), "application/pdf")}

    upload_resp = client.post("/api/documents/upload", files=files)
    assert upload_resp.status_code == 201
    doc_id = upload_resp.json()["document_id"]

    # Search for normalization
    search_payload = {
        "query": "Explain normalization and third normal form",
        "top_k": 3,
    }
    search_resp = client.post(f"/api/documents/{doc_id}/search", json=search_payload)
    assert search_resp.status_code == 200

    data = search_resp.json()
    assert data["relevant_found"] is True
    assert data["results_count"] >= 1

    top_chunk = data["results"][0]
    assert top_chunk["page"] == 2
    assert "Normalization" in top_chunk["text"]
    assert "Third Normal Form" in top_chunk["text"]
    assert top_chunk["score"] > 0.40


def test_6_document_id_filtering(client):
    """
    Requirement 6: Vectors are strictly filtered by document_id.
    """
    pdf1 = generate_dbms_normalization_pdf_bytes()
    pdf2 = generate_networks_pdf_bytes()

    res1 = client.post("/api/documents/upload", files={"file": ("DBMS.pdf", io.BytesIO(pdf1), "application/pdf")})
    res2 = client.post("/api/documents/upload", files={"file": ("Networks.pdf", io.BytesIO(pdf2), "application/pdf")})
    doc_id_1 = res1.json()["document_id"]
    doc_id_2 = res2.json()["document_id"]

    # Search Networks query against doc 1 (DBMS)
    resp = client.post(
        f"/api/documents/{doc_id_1}/search",
        json={"query": "OSPF and Dijkstra routing protocols", "top_k": 5},
    )
    assert resp.status_code == 200
    for r in resp.json()["results"]:
        # Must only return chunks belonging to doc_id_1
        assert r["document_id"] == doc_id_1
        assert r["filename"] == "DBMS.pdf"


def test_7_top_k_behavior(client):
    """Requirement 7: Configurable top_k limits returned items."""
    pdf = generate_dbms_normalization_pdf_bytes()
    upload_res = client.post("/api/documents/upload", files={"file": ("DBMS.pdf", io.BytesIO(pdf), "application/pdf")})
    doc_id = upload_res.json()["document_id"]

    # Top-K = 1
    resp_1 = client.post(
        f"/api/documents/{doc_id}/search",
        json={"query": "database systems", "top_k": 1, "similarity_threshold": 0.0},
    )
    assert len(resp_1.json()["results"]) == 1

    # Top-K = 2
    resp_2 = client.post(
        f"/api/documents/{doc_id}/search",
        json={"query": "database systems", "top_k": 2, "similarity_threshold": 0.0},
    )
    assert len(resp_2.json()["results"]) == 2


def test_8_similarity_threshold_behavior(client):
    """
    Requirement 8: Relevance threshold filters out unrelated chunks.
    When a completely unrelated query is asked with a high threshold, relevant_found is False.
    """
    pdf = generate_dbms_normalization_pdf_bytes()
    upload_res = client.post("/api/documents/upload", files={"file": ("DBMS.pdf", io.BytesIO(pdf), "application/pdf")})
    doc_id = upload_res.json()["document_id"]

    unrelated_query = "Photosynthesis chlorophyll chloroplast light dependent calvin cycle botany"
    resp = client.post(
        f"/api/documents/{doc_id}/search",
        json={
            "query": unrelated_query,
            "top_k": 5,
            "similarity_threshold": 0.50,  # High threshold
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["relevant_found"] is False
    assert data["results_count"] == 0
    assert "minimum relevance threshold" in data["message"]


def test_9_correct_page_metadata(client):
    """
    Requirement 9: Page numbers originate strictly from PDF extraction stage.
    """
    pdf = generate_dbms_normalization_pdf_bytes()
    upload_res = client.post("/api/documents/upload", files={"file": ("DBMS.pdf", io.BytesIO(pdf), "application/pdf")})
    doc_id = upload_res.json()["document_id"]

    # Query specifically for Page 1 content: NVMe flash and DRAM
    resp_p1 = client.post(
        f"/api/documents/{doc_id}/search",
        json={"query": "NVMe flash and DRAM buffer hierarchy", "top_k": 1},
    )
    assert resp_p1.status_code == 200
    assert resp_p1.json()["results"][0]["page"] == 1

    # Query specifically for Page 3 content: Multi-version concurrency control
    resp_p3 = client.post(
        f"/api/documents/{doc_id}/search",
        json={"query": "Multi-version concurrency control MVCC snapshots", "top_k": 1},
    )
    assert resp_p3.status_code == 200
    assert resp_p3.json()["results"][0]["page"] == 3


def test_10_multi_document_isolation(client):
    """
    Requirement 10: Retrieval from multiple documents has zero cross-contamination.
    """
    pdf_dbms = generate_dbms_normalization_pdf_bytes()
    pdf_net = generate_networks_pdf_bytes()

    res_dbms = client.post("/api/documents/upload", files={"file": ("DBMS.pdf", io.BytesIO(pdf_dbms), "application/pdf")})
    res_net = client.post("/api/documents/upload", files={"file": ("Networks.pdf", io.BytesIO(pdf_net), "application/pdf")})
    id_dbms = res_dbms.json()["document_id"]
    id_net = res_net.json()["document_id"]

    # Search query "TCP Three-Way Handshake" on Networks document
    resp_net = client.post(
        f"/api/documents/{id_net}/search",
        json={"query": "TCP Three-Way Handshake SYN ACK packets", "top_k": 1},
    )
    assert resp_net.status_code == 200
    net_item = resp_net.json()["results"][0]
    assert net_item["document_id"] == id_net
    assert net_item["filename"] == "Networks.pdf"
    assert "Handshake" in net_item["text"]

    # Search query "Normalization" on DBMS document
    resp_dbms = client.post(
        f"/api/documents/{id_dbms}/search",
        json={"query": "First Second Third Normal Form", "top_k": 1},
    )
    assert resp_dbms.status_code == 200
    dbms_item = resp_dbms.json()["results"][0]
    assert dbms_item["document_id"] == id_dbms
    assert dbms_item["filename"] == "DBMS.pdf"
    assert "Normal Form" in dbms_item["text"]
