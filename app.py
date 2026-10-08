"""
StudyLens AI — Your PDF-Powered AI Tutor
A Streamlit GenAI application for students learning from academic PDFs with RAG and LLM grounding.
"""

import os
import streamlit as st
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

from src.pdf_processor import PDFProcessor
from src.chunker import TextChunker
from src.embeddings import EmbeddingService
from src.vector_store import LocalVectorStore
from src.llm import LLMTutor

# ==============================================================================
# Page Configuration & Styling
# ==============================================================================
st.set_page_config(
    page_title="StudyLens AI — PDF-Powered AI Tutor",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom Styling for clean academic tutor experience
st.markdown(
    """
    <style>
    .main-header {
        font-size: 2.2rem;
        font-weight: 700;
        color: #1E293B;
        margin-bottom: 0.2rem;
    }
    .sub-header {
        font-size: 1.05rem;
        color: #475569;
        margin-bottom: 1.5rem;
    }
    .metric-card {
        background: #F8FAFC;
        border: 1px solid #E2E8F0;
        border-radius: 8px;
        padding: 12px 16px;
        margin-bottom: 12px;
    }
    .metric-val {
        font-size: 1.4rem;
        font-weight: 700;
        color: #2563EB;
    }
    .metric-lbl {
        font-size: 0.85rem;
        color: #64748B;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    .source-box {
        background-color: #F1F5F9;
        border-left: 4px solid #3B82F6;
        padding: 10px 14px;
        border-radius: 4px;
        margin-bottom: 8px;
        font-size: 0.9rem;
    }
    .source-badge {
        display: inline-block;
        background-color: #DBEAFE;
        color: #1D4ED8;
        font-size: 0.75rem;
        font-weight: 600;
        padding: 2px 8px;
        border-radius: 9999px;
        margin-right: 6px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ==============================================================================
# State Initialization
# ==============================================================================
if "messages" not in st.session_state:
    st.session_state.messages = []

if "processed_pdf" not in st.session_state:
    st.session_state.processed_pdf = None

if "vector_store" not in st.session_state:
    st.session_state.vector_store = None

if "current_file_id" not in st.session_state:
    st.session_state.current_file_id = None

# ==============================================================================
# Sidebar: Configuration & Document Controls
# ==============================================================================
with st.sidebar:
    st.markdown("### 🎓 StudyLens AI")
    st.markdown("*Your PDF-Powered Academic Tutor*")
    st.divider()

    st.markdown("#### ⚙️ AI Credentials & Model")
    provider_choice = st.selectbox(
        "LLM & Embedding Provider",
        options=["Google Gemini", "OpenAI"],
        index=0,
    )
    provider_key = "gemini" if provider_choice == "Google Gemini" else "openai"

    env_key = os.getenv("GEMINI_API_KEY") if provider_key == "gemini" else os.getenv("OPENAI_API_KEY")
    api_key_input = st.text_input(
        f"{provider_choice} API Key",
        value=env_key or "",
        type="password",
        help="Reads from .env by default. You can override it here.",
    )

    if api_key_input:
        st.success("API Key detected & active", icon="✅")
    else:
        st.warning("Please provide an API Key to enable embeddings and Q&A.", icon="⚠️")

    if provider_key == "gemini":
        model_choice = st.selectbox(
            "Gemini Model",
            options=["gemini-1.5-flash", "gemini-2.0-flash", "gemini-1.5-pro"],
            index=0,
        )
    else:
        model_choice = st.selectbox(
            "OpenAI Model",
            options=["gpt-4o-mini", "gpt-4o"],
            index=0,
        )

    st.divider()
    st.markdown("#### 📄 RAG Parameters")
    chunk_size = st.slider("Chunk Size (characters)", min_value=500, max_value=2000, value=1000, step=100)
    chunk_overlap = st.slider("Chunk Overlap (characters)", min_value=50, max_value=400, value=200, step=50)
    top_k = st.slider("Top Relevant Chunks (k)", min_value=1, max_value=8, value=4, step=1)

    st.divider()
    if st.button("🔄 Reset Document & Chat", use_container_width=True):
        if st.session_state.vector_store:
            st.session_state.vector_store.clear()
        st.session_state.processed_pdf = None
        st.session_state.vector_store = None
        st.session_state.current_file_id = None
        st.session_state.messages = []
        st.rerun()

# ==============================================================================
# Main Interface
# ==============================================================================
st.markdown('<div class="main-header">StudyLens AI — Your PDF-Powered AI Tutor</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="sub-header">Upload academic research papers, lecture notes, or textbooks to ask questions, explore concepts, and learn with grounded page citations.</div>',
    unsafe_allow_html=True,
)

# 1. Document Upload Section
uploaded_file = st.file_uploader(
    "Upload an Academic PDF",
    type=["pdf"],
    help="Upload research papers, lecture slides, textbooks, or journal articles.",
)

if uploaded_file is not None:
    file_id = f"{uploaded_file.name}_{uploaded_file.size}"

    # Process PDF only if new file is uploaded
    if st.session_state.current_file_id != file_id or st.session_state.vector_store is None:
        with st.status("📚 Processing Academic Document...", expanded=True) as status:
            try:
                # Step 1: Text extraction
                st.write("1️⃣ Extracting and normalizing text with PyMuPDF...")
                processor = PDFProcessor()
                processed_pdf = processor.process_pdf(uploaded_file, filename=uploaded_file.name)
                st.session_state.processed_pdf = processed_pdf

                # Step 2: Chunking
                st.write(f"2️⃣ Splitting {processed_pdf.total_pages} pages into coherent academic chunks...")
                chunker = TextChunker(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
                chunks = chunker.chunk_pdf(processed_pdf)

                if not chunks:
                    st.error("No valid text chunks could be produced from this document.")
                    st.stop()

                # Step 3: Embeddings
                st.write(f"3️⃣ Generating dense embeddings for {len(chunks)} chunks via {provider_choice}...")
                embedding_service = EmbeddingService(
                    provider=provider_key,
                    api_key=api_key_input,
                )
                chunk_texts = [c.text for c in chunks]
                embeddings = embedding_service.embed_documents(chunk_texts)

                # Step 4: Local Vector Store
                st.write("4️⃣ Indexing embeddings into local vector store...")
                vector_store = LocalVectorStore()
                vector_store.clear()
                vector_store.add_chunks(chunks, embeddings)

                st.session_state.vector_store = vector_store
                st.session_state.current_file_id = file_id
                st.session_state.messages = []  # Clear previous chat

                status.update(label="✅ Document Ready for Learning!", state="complete", expanded=False)
            except Exception as e:
                status.update(label="❌ Error processing document", state="error", expanded=True)
                st.error(f"Failed to process document: {str(e)}")
                st.stop()

# 2. Document Metrics Banner
if st.session_state.processed_pdf and st.session_state.vector_store:
    pdf_info = st.session_state.processed_pdf
    total_chunks = st.session_state.vector_store.count()

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(
            f'<div class="metric-card"><div class="metric-lbl">Document</div><div class="metric-val" style="font-size: 1.1rem; text-overflow: ellipsis; overflow: hidden; white-space: nowrap;">{pdf_info.filename}</div></div>',
            unsafe_allow_html=True,
        )
    with c2:
        st.markdown(
            f'<div class="metric-card"><div class="metric-lbl">Total Pages</div><div class="metric-val">{pdf_info.total_pages}</div></div>',
            unsafe_allow_html=True,
        )
    with c3:
        st.markdown(
            f'<div class="metric-card"><div class="metric-lbl">Word Count</div><div class="metric-val">{pdf_info.total_words:,}</div></div>',
            unsafe_allow_html=True,
        )
    with c4:
        st.markdown(
            f'<div class="metric-card"><div class="metric-lbl">Indexed Chunks</div><div class="metric-val">{total_chunks}</div></div>',
            unsafe_allow_html=True,
        )

    # Academic Quick Questions
    st.markdown("##### 💡 Suggested Questions:")
    quick_prompts = [
        "What are the main research questions or objectives of this paper?",
        "Explain the core methodology and theoretical approach step-by-step.",
        "Summarize the key findings, experimental results, and conclusions.",
    ]
    qp_cols = st.columns(len(quick_prompts))
    selected_quick_prompt = None
    for i, qp in enumerate(quick_prompts):
        with qp_cols[i]:
            if st.button(qp, key=f"qp_{i}", use_container_width=True):
                selected_quick_prompt = qp

    st.divider()

    # 3. Chat History Display
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if "sources" in msg and msg["sources"]:
                with st.expander(f"📚 Retrieved Context Sources ({len(msg['sources'])} excerpts)", expanded=False):
                    for idx, src in enumerate(msg["sources"], 1):
                        st.markdown(
                            f"""<div class="source-box">
                            <span class="source-badge">Page {src.get('page_number', '?')}</span>
                            <span class="source-badge">Relevance: {int(src.get('score', 0) * 100)}%</span>
                            <span class="source-badge">ID: {src.get('chunk_id', '')}</span>
                            <div style="margin-top: 6px; color: #334155;">{src.get('text', '')}</div>
                            </div>""",
                            unsafe_allow_html=True,
                        )

    # 4. User Question Input
    user_input = st.chat_input("Ask your tutor a question about this document...")
    query_to_run = selected_quick_prompt or user_input

    if query_to_run:
        # Check API key before running
        if not api_key_input:
            st.error("Please provide a valid API Key in the sidebar to ask questions.")
            st.stop()

        # Append and display user question
        st.session_state.messages.append({"role": "user", "content": query_to_run})
        with st.chat_message("user"):
            st.markdown(query_to_run)

        # Tutor Response Generation
        with st.chat_message("assistant"):
            with st.spinner("🔍 Retrieving relevant academic excerpts and synthesizing tutor explanation..."):
                try:
                    # Step 1: Embed query
                    emb_svc = EmbeddingService(provider=provider_key, api_key=api_key_input)
                    q_embedding = emb_svc.embed_query(query_to_run)

                    # Step 2: Retrieve top-k chunks
                    retrieved_chunks = st.session_state.vector_store.search(q_embedding, top_k=top_k)

                    # Step 3: LLM generation
                    tutor = LLMTutor(
                        provider=provider_key,
                        api_key=api_key_input,
                        model_name=model_choice,
                    )
                    response_data = tutor.answer_question(
                        question=query_to_run,
                        retrieved_chunks=retrieved_chunks,
                        conversation_history=st.session_state.messages[:-1],
                    )

                    answer_text = response_data["answer"]
                    sources = response_data["sources"]

                    # Display Answer
                    st.markdown(answer_text)

                    # Display Sources
                    if sources:
                        with st.expander(f"📚 Retrieved Context Sources ({len(sources)} excerpts)", expanded=False):
                            for idx, src in enumerate(sources, 1):
                                st.markdown(
                                    f"""<div class="source-box">
                                    <span class="source-badge">Page {src.get('page_number', '?')}</span>
                                    <span class="source-badge">Relevance: {int(src.get('score', 0) * 100)}%</span>
                                    <span class="source-badge">ID: {src.get('chunk_id', '')}</span>
                                    <div style="margin-top: 6px; color: #334155;">{src.get('text', '')}</div>
                                    </div>""",
                                    unsafe_allow_html=True,
                                )

                    # Save to chat history
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": answer_text,
                        "sources": sources,
                    })

                except Exception as e:
                    error_msg = f"Error generating answer: {str(e)}"
                    st.error(error_msg)
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": error_msg,
                        "sources": [],
                    })
else:
    # Helpful empty state guide
    st.info("👆 Please upload an academic PDF document above to get started.", icon="💡")
    with st.container():
        st.markdown(
            """
            ### How StudyLens AI Works:
            1. **Upload Academic PDF**: PyMuPDF extracts full text while preserving page numbers and formatting.
            2. **Smart Semantic Chunking**: The document is partitioned into coherent academic blocks with sentence preservation.
            3. **Dense Vector Embeddings**: Generates embeddings for each block.
            4. **Local Vector Storage**: Chunks and embeddings are indexed locally using ChromaDB.
            5. **Grounded Tutor Answers**: The LLM synthesizes an educational explanation strictly grounded in the retrieved sources, with direct page citations.
            """
        )
