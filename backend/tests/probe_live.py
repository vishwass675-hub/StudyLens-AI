"""
Live HTTP probe against running FastAPI server.
Verifies complete pipeline:
Health -> PDF Upload -> Page Extraction -> Chunking -> Vector Search -> Chat API.
"""

import sys
import os
import requests
import io

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from backend.tests.conftest import generate_dbms_normalization_pdf_bytes

BASE_URL = "http://127.0.0.1:8000"

print("--- 1. Testing GET /api/health ---")
r_health = requests.get(f"{BASE_URL}/api/health")
print("Response:", r_health.status_code, r_health.json())
assert r_health.status_code == 200
assert r_health.json() == {"status": "ok"}
print("[PASS] Health check verified.")

print("\n--- 2. Testing POST /api/documents/upload ---")
pdf_bytes = generate_dbms_normalization_pdf_bytes()
files = {"file": ("DBMS_Normalization_Lecture.pdf", io.BytesIO(pdf_bytes), "application/pdf")}
r_upload = requests.post(f"{BASE_URL}/api/documents/upload", files=files)
print("Response:", r_upload.status_code, r_upload.json())
assert r_upload.status_code == 201
doc_meta = r_upload.json()
doc_id = doc_meta["document_id"]
assert doc_id.startswith("doc_")
assert doc_meta["filename"] == "DBMS_Normalization_Lecture.pdf"
assert doc_meta["page_count"] == 3
assert doc_meta["status"] == "ready"
print(f"[PASS] Upload & vector indexing verified for {doc_id}.")

print(f"\n--- 3. Testing POST /api/documents/{doc_id}/search ('Explain normalization') ---")
query_text = "Explain normalization and third normal form"
search_payload = {
    "query": query_text,
    "top_k": 3,
}
r_search = requests.post(f"{BASE_URL}/api/documents/{doc_id}/search", json=search_payload)
print("Search Response Status:", r_search.status_code)
search_data = r_search.json()
assert r_search.status_code == 200
assert search_data["relevant_found"] is True

top_result = search_data["results"][0]
print(f"\n[TOP RETRIEVED CHUNK]")
print(f"  - Chunk ID:    {top_result['chunk_id']}")
print(f"  - Page Number: {top_result['page']}")
print(f"  - Score:       {top_result['score']:.4f}")
print(f"  - Excerpt:     {top_result['text'][:120]}...")
assert top_result["page"] == 2
print("[PASS] Semantic vector retrieval successfully returned Page 2 with high similarity score!")

print("\n--- 4. Testing POST /api/chat with Unrelated Query (No-Relevant-Context Behavior) ---")
unrelated_chat_payload = {
    "document_id": doc_id,
    "message": "Photosynthesis chlorophyll thylakoid light reactions botany biology",
    "mode": "simple",
    "similarity_threshold": 0.35,
}
r_unrelated_chat = requests.post(f"{BASE_URL}/api/chat", json=unrelated_chat_payload)
print("Unrelated chat response:", r_unrelated_chat.status_code, r_unrelated_chat.json())
assert r_unrelated_chat.status_code == 200
unrelated_chat_data = r_unrelated_chat.json()
assert "I couldn't find enough information about that in the uploaded document." in unrelated_chat_data["answer"]
assert unrelated_chat_data["sources"] == []
print("[PASS] Controlled no-relevant-context response verified without hallucination!")

print("\n" + "=" * 60)
print("[SUCCESS] ALL LIVE EMBEDDING, VECTOR & CHAT PROBES PASSED!")
print("=" * 60)
