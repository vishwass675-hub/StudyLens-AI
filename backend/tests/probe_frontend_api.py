"""
Verification script testing all frontend API client methods against live backend.
"""

import requests

BASE_URL = "http://127.0.0.1:8000"

# 1. Health check
res = requests.get(f"{BASE_URL}/api/health")
assert res.status_code == 200
print("[PASS] 1. Health check: OK")

# 2. Upload Document
with open("backend/data/sample_dbms_lecture.pdf", "rb") as f:
    files = {"file": ("sample_dbms_lecture.pdf", f, "application/pdf")}
    up_res = requests.post(f"{BASE_URL}/api/documents/upload", files=files)
assert up_res.status_code == 201
doc_data = up_res.json()
doc_id = doc_data["document_id"]
assert doc_data["status"] == "ready"
assert doc_data["page_count"] == 3
print(f"[PASS] 2. Upload & Ingestion: OK (doc_id={doc_id}, pages={doc_data['page_count']})")

# 3. Get Document Status
stat_res = requests.get(f"{BASE_URL}/api/documents/{doc_id}")
assert stat_res.status_code == 200
stat_data = stat_res.json()
assert stat_data["status"] == "ready"
print(f"[PASS] 3. Document status: OK (filename={stat_data['filename']}, status={stat_data['status']})")

# 4. Search Document
search_res = requests.post(
    f"{BASE_URL}/api/documents/{doc_id}/search",
    json={"query": "What is third normal form?", "top_k": 3},
)
assert search_res.status_code == 200
search_data = search_res.json()
assert search_data["relevant_found"] is True
print(f"[PASS] 4. Search Document: OK ({len(search_data['results'])} chunks found, top page={search_data['results'][0]['page']})")

# 5. List Documents
list_res = requests.get(f"{BASE_URL}/api/documents")
assert list_res.status_code == 200
docs = list_res.json()["documents"]
assert len(docs) >= 1
print(f"[PASS] 5. List Documents: OK ({len(docs)} documents registered)")

# 6. Chat with No Relevant Context (Unrelated topic)
chat_res = requests.post(
    f"{BASE_URL}/api/chat",
    json={
        "document_id": doc_id,
        "message": "Explain black holes and general relativity astrophysics",
        "mode": "simple",
        "similarity_threshold": 0.35,
    },
)
assert chat_res.status_code == 200
chat_data = chat_res.json()
assert "I couldn't find enough information about that in the uploaded document." in chat_data["answer"]
assert chat_data["sources"] == []
print("[PASS] 6. Chat endpoint: Controlled anti-hallucination rejection verified.")

print("\n" + "=" * 60)
print("ALL FRONTEND API CONTRACTS SUCCESSFULLY VERIFIED AGAINST LIVE BACKEND!")
print("=" * 60)
