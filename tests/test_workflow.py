"""
End-to-End Workflow Verification Script for StudyLens AI.
Tests:
1. Academic PDF synthesis & PyMuPDF extraction
2. Text chunking with page number tracking
3. Embedding generation
4. Local vector store indexing (ChromaDB + fallback)
5. Semantic vector retrieval & scoring
6. Grounded LLM Tutor prompt generation & answer structure
"""

import sys
import os

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pymupdf as fitz

from src.pdf_processor import PDFProcessor
from src.chunker import TextChunker
from src.embeddings import EmbeddingService
from src.vector_store import LocalVectorStore
from src.llm import LLMTutor


def create_sample_academic_pdf(filepath: str):
    """Creates a realistic multi-page academic sample PDF for verification."""
    doc = fitz.open()

    # Page 1: Abstract and Introduction
    page1 = doc.new_page()
    text_p1 = (
        "StudyLens Research Paper: Attention Mechanisms in Deep Learning\n\n"
        "Abstract\n"
        "In this study, we evaluate transformer self-attention mechanisms applied to multimodal learning. "
        "Our experiments indicate that multi-head attention yields a 14.2% accuracy improvement over recurrent networks. "
        "The quadratic complexity O(N^2) remains a primary challenge for ultra-long context sequences.\n\n"
        "1. Introduction\n"
        "Deep neural networks have revolutionized natural language processing and computer vision. "
        "Historically, recurrent neural networks (RNNs) and LSTMs were the standard for sequence modeling. "
        "However, sequential computation prevents parallelization across token positions during training."
    )
    page1.insert_text(fitz.Point(50, 72), text_p1, fontsize=11)

    # Page 2: Methodology and Equations
    page2 = doc.new_page()
    text_p2 = (
        "2. Mathematical Methodology\n"
        "The scaled dot-product attention computes outputs as follows:\n"
        "Attention(Q, K, V) = softmax(Q * K^T / sqrt(d_k)) * V\n\n"
        "Where Q, K, and V represent Queries, Keys, and Values matrices respectively. "
        "The scaling factor sqrt(d_k) prevents the dot products from growing excessively large for high dimensions. "
        "Multi-head attention projects queries, keys, and values h times with independently learned parameter matrices.\n\n"
        "3. Experimental Setup\n"
        "We trained the architecture on the AcademicDocs benchmark using 8 NVIDIA A100 GPUs for 100 epochs. "
        "Adam optimizer was used with beta1=0.9, beta2=0.98, and an inverse square root learning rate schedule."
    )
    page2.insert_text(fitz.Point(50, 72), text_p2, fontsize=11)

    # Page 3: Results and Limitations
    page3 = doc.new_page()
    text_p3 = (
        "4. Results & Discussion\n"
        "The proposed transformer achieved a BLEU score of 28.4 on English-to-German translation tasks. "
        "Ablation studies confirmed that removing positional encodings causes performance degradation of over 40%.\n\n"
        "5. Limitations and Future Work\n"
        "A key limitation noted in this work is memory consumption during inference with large batch sizes. "
        "Future directions include exploring linear attention approximations and sparse kernel projections."
    )
    page3.insert_text(fitz.Point(50, 72), text_p3, fontsize=11)

    doc.save(filepath)
    doc.close()
    print(f"[TEST] Created sample academic PDF with 3 pages at: {filepath}")


def run_full_verification():
    test_pdf_path = "test_sample_paper.pdf"
    try:
        # Step 1: Create sample PDF
        create_sample_academic_pdf(test_pdf_path)

        # Step 2: PDF Processing
        print("\n--- Step 1: Testing PDF Processing ---")
        processor = PDFProcessor()
        processed_pdf = processor.process_pdf(test_pdf_path, filename="test_sample_paper.pdf")
        print(f"Extracted pages: {processed_pdf.total_pages}")
        print(f"Extracted words: {processed_pdf.total_words}")
        print(f"Extracted chars: {processed_pdf.total_chars}")
        assert processed_pdf.total_pages == 3, f"Expected 3 pages, got {processed_pdf.total_pages}"
        assert processed_pdf.total_words > 100, "Word count too low"
        assert "Attention(Q, K, V)" in processed_pdf.pages[1].text, "Equation missing from Page 2"
        print("[PASS] PDF Processing passed!")

        # Step 3: Text Chunking
        print("\n--- Step 2: Testing Chunking ---")
        chunker = TextChunker(chunk_size=500, chunk_overlap=100)
        chunks = chunker.chunk_pdf(processed_pdf)
        print(f"Generated {len(chunks)} chunks.")
        assert len(chunks) >= 3, f"Expected at least 3 chunks, got {len(chunks)}"
        # Verify page provenance
        pages_represented = {c.page_number for c in chunks}
        assert 1 in pages_represented and 2 in pages_represented and 3 in pages_represented, "Missing pages in chunks"
        print(f"Chunk page distribution: {pages_represented}")
        print("[PASS] Chunking passed!")

        # Step 4: Embeddings
        print("\n--- Step 3: Testing Embeddings ---")
        # Test local fallback embeddings (works offline / zero-network)
        emb_service = EmbeddingService(provider="local")
        chunk_texts = [c.text for c in chunks]
        embeddings = emb_service.embed_documents(chunk_texts)
        assert len(embeddings) == len(chunks), "Embeddings count does not match chunks"
        assert len(embeddings[0]) == 384, f"Expected 384 dimensions, got {len(embeddings[0])}"

        # Test query embedding
        query = "What is the mathematical formula for attention?"
        q_emb = emb_service.embed_query(query)
        assert len(q_emb) == 384, "Query embedding dimension mismatch"
        print("[PASS] Embedding generation passed!")

        # Step 5: Local Vector Store
        print("\n--- Step 4: Testing Local Vector Store (ChromaDB) ---")
        vector_store = LocalVectorStore(persist_directory="./data/test_chroma_db", collection_name="test_col")
        vector_store.clear()
        indexed_count = vector_store.add_chunks(chunks, embeddings)
        assert indexed_count == len(chunks), f"Expected {len(chunks)} indexed, got {indexed_count}"

        # Search
        results = vector_store.search(q_emb, top_k=2)
        print(f"Retrieved {len(results)} results:")
        for r in results:
            print(f"  - Chunk: {r['chunk_id']} | Page: {r['page_number']} | Score: {r['score']}")
            print(f"    Excerpt: {r['text'][:90]}...")

        assert len(results) > 0, "Vector search returned no results"
        print("[PASS] Local Vector Store passed!")

        # Step 6: LLM Tutor
        print("\n--- Step 5: Testing LLM Tutor formatting & generation ---")
        tutor = LLMTutor(provider="local")
        tutor_response = tutor.answer_question(query, results)
        assert "answer" in tutor_response, "Tutor response missing answer field"
        assert len(tutor_response["sources"]) == len(results), "Sources mismatch in tutor response"
        print("Tutor response preview:")
        print(tutor_response["answer"][:250])
        print("[PASS] LLM Tutor passed!")

        print("\n" + "=" * 60)
        print("[SUCCESS] ALL CORE WORKFLOW VERIFICATIONS PASSED SUCCESSFULLY!")
        print("=" * 60)

    finally:
        # Clean up test files
        if os.path.exists(test_pdf_path):
            os.remove(test_pdf_path)


if __name__ == "__main__":
    run_full_verification()
