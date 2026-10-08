"""
Pytest fixtures and PDF helpers for StudyLens AI backend tests.
"""

import io
import os
import sys

# Ensure root workspace is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import pytest
import pymupdf as fitz
from fastapi.testclient import TestClient

from backend.main import app
from backend.app.core.config import settings
from backend.app.services.vector_store import vector_store


from backend.app.db.database import database_mgr
from backend.app.services.document_service import document_service


@pytest.fixture
def client():
    """FastAPI TestClient fixture."""
    return TestClient(app)


@pytest.fixture(autouse=True)
def cleanup_test_state():
    """Cleans up uploads directory, vector database, and SQLite records before and after each test."""
    def _clean():
        vector_store.clear()
        document_service._documents.clear()
        if os.path.exists(settings.UPLOAD_DIR):
            for f in os.listdir(settings.UPLOAD_DIR):
                file_path = os.path.join(settings.UPLOAD_DIR, f)
                if os.path.isfile(file_path):
                    try:
                        os.remove(file_path)
                    except OSError:
                        pass
        try:
            with database_mgr.get_connection() as conn:
                conn.execute("DELETE FROM messages;")
                conn.execute("DELETE FROM conversations;")
                conn.execute("DELETE FROM study_results;")
                conn.execute("DELETE FROM pages;")
                conn.execute("DELETE FROM documents;")
                conn.commit()
        except Exception:
            pass

    _clean()
    yield
    _clean()


def generate_valid_pdf_bytes() -> bytes:
    """Creates a real 3-page academic PDF with text and formulas."""
    doc = fitz.open()

    # Page 1
    p1 = doc.new_page()
    text_p1 = (
        "Database Management Systems (DBMS)\n"
        "Chapter 1: Relational Model\n\n"
        "A relational database consists of a collection of tables, each of which is assigned a unique name. "
        "A row in a table represents a relationship among a set of values. "
        "The relational data model was originally introduced by Edgar F. Codd in 1970."
    )
    p1.insert_text(fitz.Point(50, 72), text_p1, fontsize=11)

    # Page 2
    p2 = doc.new_page()
    text_p2 = (
        "Chapter 2: Relational Algebra & Queries\n\n"
        "The fundamental operations in relational algebra are select, project, union, set difference, "
        "Cartesian product, and rename. Selection sigma_p(r) filters tuples satisfying predicate p. "
        "Projection pi_A(r) extracts columns specified in attribute list A."
    )
    p2.insert_text(fitz.Point(50, 72), text_p2, fontsize=11)

    # Page 3
    p3 = doc.new_page()
    text_p3 = (
        "Chapter 3: Transactions & ACID Properties\n\n"
        "A transaction is a unit of program execution that accesses and possibly updates various data items. "
        "The ACID properties ensure reliable database processing:\n"
        "1. Atomicity: All or nothing execution.\n"
        "2. Consistency: Correctness constraints preserved.\n"
        "3. Isolation: Transactions execute concurrently without interference.\n"
        "4. Durability: Committed updates survive system crashes."
    )
    p3.insert_text(fitz.Point(50, 72), text_p3, fontsize=11)

    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


def generate_dbms_normalization_pdf_bytes() -> bytes:
    """Creates a 3-page PDF specifically focusing on Database Normalization on Page 2."""
    doc = fitz.open()

    # Page 1: Introduction
    p1 = doc.new_page()
    text_p1 = (
        "Advanced Database Systems — Lecture Series\n"
        "Section 1: Data Storage and File Structures\n\n"
        "Modern storage systems employ hybrid memory hierarchies combining NVMe flash and DRAM buffers. "
        "Storage engines organize disk blocks into slotted pages with record headers and tuple pointers."
    )
    p1.insert_text(fitz.Point(50, 72), text_p1, fontsize=11)

    # Page 2: Normalization
    p2 = doc.new_page()
    text_p2 = (
        "Section 2: Database Normalization and Schema Decomposition\n\n"
        "Normalization is the rigorous systematic process of organizing relation schemas to reduce data redundancy "
        "and eliminate update anomalies, insertion anomalies, and deletion anomalies.\n\n"
        "First Normal Form (1NF) requires all attribute domains to be atomic values with no repeating groups.\n"
        "Second Normal Form (2NF) enforces that all non-prime attributes are fully functionally dependent on candidate keys.\n"
        "Third Normal Form (3NF) requires eliminating transitive dependencies: for every non-trivial functional dependency "
        "X -> A, either X is a superkey or A is a prime attribute.\n"
        "Boyce-Codd Normal Form (BCNF) strictly requires every determinant X in functional dependency X -> A to be a superkey."
    )
    p2.insert_text(fitz.Point(50, 72), text_p2, fontsize=11)

    # Page 3: Concurrency Control
    p3 = doc.new_page()
    text_p3 = (
        "Section 3: Distributed Concurrency Control\n\n"
        "Multi-version concurrency control (MVCC) creates logical snapshots of tuple versions. "
        "Read operations never block write operations, eliminating contention for analytical workloads."
    )
    p3.insert_text(fitz.Point(50, 72), text_p3, fontsize=11)

    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


def generate_networks_pdf_bytes() -> bytes:
    """Creates a 3-page PDF covering Computer Networks (completely distinct topic)."""
    doc = fitz.open()

    p1 = doc.new_page()
    p1.insert_text(fitz.Point(50, 72), "Computer Networks: Physical Layer, Fiber Optics, and Ethernet standards.", fontsize=11)

    p2 = doc.new_page()
    p2.insert_text(fitz.Point(50, 72), "Routing Protocols: Dijkstra Shortest Path, Open Shortest Path First (OSPF), Border Gateway Protocol (BGP).", fontsize=11)

    p3 = doc.new_page()
    p3.insert_text(fitz.Point(50, 72), "Transport Layer: TCP Three-Way Handshake, Flow Control Window, SYN ACK packets.", fontsize=11)

    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


def generate_empty_pdf_bytes() -> bytes:
    """Creates a valid PDF document with 1 blank page (zero extractable text)."""
    doc = fitz.open()
    doc.new_page()
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes
