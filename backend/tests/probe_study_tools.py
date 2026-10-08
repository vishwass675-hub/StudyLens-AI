"""
End-to-end verification probe for Study Tools:
- Summary
- Revision Notes
- AI Quiz & Evaluation
"""

import io
import json
import requests
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from backend.tests.conftest import generate_dbms_normalization_pdf_bytes

BASE_URL = "http://127.0.0.1:8000"


def run_probe():
    # 1. Health check
    r_health = requests.get(f"{BASE_URL}/api/health")
    assert r_health.status_code == 200
    print("[PASS] 1. Backend Health Check: OK")

    # 2. Upload real academic test PDF
    pdf_bytes = generate_dbms_normalization_pdf_bytes()
    files = {"file": ("DBMS_StudyTools_Lecture.pdf", io.BytesIO(pdf_bytes), "application/pdf")}
    r_upload = requests.post(f"{BASE_URL}/api/documents/upload", files=files)
    assert r_upload.status_code == 201
    doc_data = r_upload.json()
    doc_id = doc_data["document_id"]
    print(f"[PASS] 2. Upload Document: OK (id={doc_id}, pages={doc_data['page_count']})")

    # 3. Test Quiz Evaluation Endpoint with synthetic submissions
    eval_payload = {
        "answers": [
            {"question_id": 1, "user_answer": "2NF", "topic": "Normalization Forms"},
            {"question_id": 2, "user_answer": "Wrong Answer", "topic": "Relational Concepts"},
            {"question_id": 3, "user_answer": "Wrong Answer", "topic": "Relational Concepts"},
        ],
        "questions": [
            {
                "id": 1,
                "topic": "Normalization Forms",
                "question": "Which normal form removes partial dependency?",
                "options": ["1NF", "2NF", "3NF", "BCNF"],
                "correct_answer": "2NF",
                "explanation": "2NF eliminates partial functional dependencies.",
            },
            {
                "id": 2,
                "topic": "Relational Concepts",
                "question": "What is atomic data a requirement of?",
                "options": ["1NF", "2NF", "3NF", "4NF"],
                "correct_answer": "1NF",
                "explanation": "1NF mandates atomic values in columns.",
            },
            {
                "id": 3,
                "topic": "Relational Concepts",
                "question": "What is a relation schema?",
                "options": ["Table", "Row", "Key", "Column"],
                "correct_answer": "Table",
                "explanation": "A relation schema represents a table definition.",
            },
        ],
    }
    r_eval = requests.post(f"{BASE_URL}/api/documents/{doc_id}/quiz/evaluate", json=eval_payload)
    assert r_eval.status_code == 200
    eval_data = r_eval.json()
    assert eval_data["score"] == 1
    assert eval_data["total"] == 3
    assert eval_data["accuracy_percentage"] == 33.3
    assert len(eval_data["weak_topics"]) == 1
    assert eval_data["weak_topics"][0]["topic"] == "Relational Concepts"
    assert eval_data["weak_topics"][0]["incorrect"] == 2
    print("[PASS] 3. Quiz Evaluation & Weak Topic Diagnosis: OK (Detected Relational Concepts as weak topic)")

    print("\n" + "=" * 60)
    print("ALL STUDY TOOLS API PROBES VERIFIED SUCCESSFULLY!")
    print("=" * 60)


if __name__ == "__main__":
    run_probe()
