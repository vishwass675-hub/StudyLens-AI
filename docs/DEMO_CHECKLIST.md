# StudyLens AI — Demonstration & Verification Checklist

Use this checklist to run a live demonstration of StudyLens AI or verify deployment readiness.

---

## Pre-Flight Setup
- [ ] Backend dependencies installed (`pip install -r backend/requirements.txt`)
- [ ] Frontend dependencies installed (`cd frontend && npm install`)
- [ ] Environment file configured (`backend/.env` with `OLLAMA_API_KEY`)
- [ ] Backend server running on `http://127.0.0.1:8000` (`python -m uvicorn backend.main:app --reload`)
- [ ] Frontend application running on `http://localhost:3000` (`npm run dev`)

---

## Live Demonstration Checklist

### 1. Ingestion & Document Library
- [ ] **Backend Starts**: `GET /api/health` returns `{"status": "ok"}` and `GET /api/health/ready` returns operational readiness.
- [ ] **Frontend Starts**: App loads at `http://localhost:3000` with the StudyLens AI layout and sidebar.
- [ ] **Empty State**: Displays `📚 No documents yet` if no PDF is uploaded.
- [ ] **PDF Upload Works**: Select an academic PDF (e.g., lecture notes or textbook chapter).
- [ ] **PDF Processing Works**: Extraction preserves page numbers and character counts.
- [ ] **Embeddings Generated**: Text chunks are embedded and indexed into the local vector store.
- [ ] **Document Library Updated**: Sidebar displays filename, page count, status pill (Ready), upload date, and last accessed time.

### 2. Grounded Tutoring & Chat History
- [ ] **Tutor Question Works**: Ask a specific conceptual question about the uploaded PDF.
- [ ] **Retrieval Works**: Relevant chunks are retrieved strictly from the active document.
- [ ] **Nemotron Response Works**: Nemotron 3 Nano returns an explanation grounded in the text.
- [ ] **Sources Display Correctly**: Response includes clickable page citations pointing to source pages.
- [ ] **Tutor Pedagogical Modes**: Switch between `simple`, `detailed`, `exam`, and `eli5` modes and observe adaptive explanations.
- [ ] **Automatic Titling Works**: Conversation is auto-titled with a clean summary of the initial question.
- [ ] **Follow-Up Question Works**: Ask a follow-up; multi-turn conversation context is bounded and maintained.
- [ ] **New Conversation**: Click "+ New Chat" to start a fresh thread for the same document.

### 3. Study Tools
- [ ] **Summary Generator**: Click "Summary" tab to view document overview, key topics, takeaways, definitions, and exam points.
- [ ] **Revision Notes**: Click "Revision Notes" tab to view structured markdown study notes.
- [ ] **AI Quiz**: Click "AI Quiz" tab, take the interactive MCQ quiz, view instant answer explanations, and examine weak topic analysis.

### 4. Persistence & Document Management
- [ ] **Persistence Works**: Data is persisted in SQLite (`studylens.db`).
- [ ] **Browser Refresh Works**: Refresh the browser page (`F5`). Active document, conversation history, and messages are completely restored.
- [ ] **Document Switching**: Switch between uploaded PDFs. Verifies that retrieval never leaks context across documents.
- [ ] **Safe Deletion**: Click the trash icon on a document, confirm the deletion dialog, and verify document metadata, vector chunks, cached study results, and uploaded PDF are permanently purged.

### 5. Security & Build
- [ ] **No API Key Exposed**: Browser network tab inspection confirms `OLLAMA_API_KEY` is never sent to the client.
- [ ] **Production Build Succeeds**: `npm run build` in `frontend` compiles with 0 errors.
- [ ] **Test Suite Passes**: `pytest backend/tests` executes with 100% pass rate.
