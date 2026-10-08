/**
 * StudyLens AI Frontend API Client
 * Clean abstraction over the FastAPI backend endpoints.
 * Never makes direct raw fetch calls from React components.
 */

import {
  DocumentMetadata,
  ChatRequest,
  ChatResponse,
  SearchResponse,
} from "./types";

const API_BASE_URL = (
  process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000"
).replace(/\/$/, "");

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
    this.name = "ApiError";
  }
}

function sanitizeErrorMessage(status: number, rawDetail?: string): string {
  if (status === 0 || !rawDetail) {
    return "The StudyLens AI backend is currently unreachable. Please ensure the backend server is running.";
  }
  if (status === 404) {
    return "The requested document or resource was not found. Please re-upload your document.";
  }
  if (status === 400) {
    return rawDetail || "Invalid request. Please check the uploaded file or input.";
  }
  if (status === 422) {
    return rawDetail || "The provided PDF document could not be processed or is empty.";
  }
  if (status === 502) {
    return "The AI tutor model is currently experiencing connectivity issues. Please try again in a few moments.";
  }
  if (status >= 500) {
    return "An internal server error occurred while processing your request. Please try again.";
  }
  return rawDetail || "An unexpected error occurred. Please try again.";
}

export const api = {
  /**
   * Health check to probe if the FastAPI backend is running and healthy.
   */
  async checkHealth(): Promise<boolean> {
    try {
      const res = await fetch(`${API_BASE_URL}/api/health`, {
        method: "GET",
        signal: AbortSignal.timeout(3000),
      });
      return res.ok;
    } catch {
      return false;
    }
  },

  /**
   * Upload an academic PDF to the FastAPI backend for text extraction, chunking, and vector indexing.
   * Endpoint: POST /api/documents/upload
   */
  async uploadDocument(
    file: File,
    chunkSize?: number,
    chunkOverlap?: number
  ): Promise<DocumentMetadata> {
    // 1. Client-side file validation
    if (!file.name.toLowerCase().endsWith(".pdf")) {
      throw new ApiError(400, "Please upload a valid PDF file.");
    }
    const maxSizeBytes = 50 * 1024 * 1024;
    if (file.size > maxSizeBytes) {
      throw new ApiError(400, "The PDF file size exceeds the 50MB limit.");
    }

    const formData = new FormData();
    formData.append("file", file);
    if (chunkSize) {
      formData.append("chunk_size", chunkSize.toString());
    }
    if (chunkOverlap) {
      formData.append("chunk_overlap", chunkOverlap.toString());
    }

    try {
      const res = await fetch(`${API_BASE_URL}/api/documents/upload`, {
        method: "POST",
        body: formData,
      });

      if (!res.ok) {
        const errJson = await res.json().catch(() => ({}));
        const message = sanitizeErrorMessage(res.status, errJson.detail);
        throw new ApiError(res.status, message);
      }

      const data = await res.json();
      return {
        ...data,
        total_pages: data.page_count,
      };
    } catch (err: unknown) {
      if (err instanceof ApiError) throw err;
      throw new ApiError(0, sanitizeErrorMessage(0));
    }
  },

  /**
   * Retrieve document processing status and full metadata.
   * Endpoint: GET /api/documents/{documentId}
   */
  async getDocumentStatus(documentId: string): Promise<DocumentMetadata> {
    try {
      const res = await fetch(`${API_BASE_URL}/api/documents/${encodeURIComponent(documentId)}`);
      if (!res.ok) {
        const errJson = await res.json().catch(() => ({}));
        throw new ApiError(res.status, sanitizeErrorMessage(res.status, errJson.detail));
      }
      const data = await res.json();
      return {
        ...data,
        total_pages: data.page_count,
      };
    } catch (err: unknown) {
      if (err instanceof ApiError) throw err;
      throw new ApiError(0, sanitizeErrorMessage(0));
    }
  },

  /**
   * List all uploaded documents currently registered in the backend.
   * Endpoint: GET /api/documents
   */
  async listDocuments(): Promise<DocumentMetadata[]> {
    try {
      const res = await fetch(`${API_BASE_URL}/api/documents`);
      if (!res.ok) return [];
      const data = await res.json();
      return (data.documents || []).map((d: DocumentMetadata) => ({
        ...d,
        total_pages: d.page_count,
      }));
    } catch {
      return [];
    }
  },

  /**
   * Returns direct URL to stream or download the saved PDF file.
   */
  getDocumentFileUrl(documentId: string): string {
    return `${API_BASE_URL}/api/documents/${encodeURIComponent(documentId)}/file`;
  },

  /**
   * Safely delete a document and its associated vectors, conversations, messages, and files.
   * Endpoint: DELETE /api/documents/{documentId}
   */
  async deleteDocument(documentId: string): Promise<boolean> {
    try {
      const res = await fetch(
        `${API_BASE_URL}/api/documents/${encodeURIComponent(documentId)}`,
        { method: "DELETE" }
      );
      if (!res.ok && res.status !== 404) {
        const errJson = await res.json().catch(() => ({}));
        throw new ApiError(res.status, sanitizeErrorMessage(res.status, errJson.detail));
      }
      return true;
    } catch (err: unknown) {
      if (err instanceof ApiError) throw err;
      throw new ApiError(0, sanitizeErrorMessage(0));
    }
  },

  /**
   * List persistent conversations, optionally filtered by active document ID.
   * Endpoint: GET /api/conversations
   */
  async listConversations(documentId?: string): Promise<import("./types").Conversation[]> {
    try {
      const url = documentId
        ? `${API_BASE_URL}/api/conversations?document_id=${encodeURIComponent(documentId)}`
        : `${API_BASE_URL}/api/conversations`;
      const res = await fetch(url);
      if (!res.ok) return [];
      const data = await res.json();
      return data.conversations || [];
    } catch {
      return [];
    }
  },

  /**
   * Create a new persistent conversation for a document.
   * Endpoint: POST /api/conversations
   */
  async createConversation(
    documentId: string,
    title?: string
  ): Promise<import("./types").Conversation> {
    try {
      const res = await fetch(`${API_BASE_URL}/api/conversations`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ document_id: documentId, title }),
      });
      if (!res.ok) {
        const errJson = await res.json().catch(() => ({}));
        throw new ApiError(res.status, sanitizeErrorMessage(res.status, errJson.detail));
      }
      return res.json();
    } catch (err: unknown) {
      if (err instanceof ApiError) throw err;
      throw new ApiError(0, sanitizeErrorMessage(0));
    }
  },

  /**
   * Get conversation details.
   * Endpoint: GET /api/conversations/{conversationId}
   */
  async getConversation(conversationId: string): Promise<import("./types").Conversation> {
    try {
      const res = await fetch(
        `${API_BASE_URL}/api/conversations/${encodeURIComponent(conversationId)}`
      );
      if (!res.ok) {
        const errJson = await res.json().catch(() => ({}));
        throw new ApiError(res.status, sanitizeErrorMessage(res.status, errJson.detail));
      }
      return res.json();
    } catch (err: unknown) {
      if (err instanceof ApiError) throw err;
      throw new ApiError(0, sanitizeErrorMessage(0));
    }
  },

  /**
   * Rename an existing conversation.
   * Endpoint: PATCH /api/conversations/{conversationId}
   */
  async updateConversationTitle(
    conversationId: string,
    title: string
  ): Promise<import("./types").Conversation> {
    try {
      const res = await fetch(
        `${API_BASE_URL}/api/conversations/${encodeURIComponent(conversationId)}`,
        {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ title }),
        }
      );
      if (!res.ok) {
        const errJson = await res.json().catch(() => ({}));
        throw new ApiError(res.status, sanitizeErrorMessage(res.status, errJson.detail));
      }
      return res.json();
    } catch (err: unknown) {
      if (err instanceof ApiError) throw err;
      throw new ApiError(0, sanitizeErrorMessage(0));
    }
  },

  /**
   * Automatically summarize what was texted in chat and set as conversation title.
   * Endpoint: POST /api/conversations/{conversationId}/summarize-title
   */
  async summarizeConversationTitle(
    conversationId: string
  ): Promise<import("./types").Conversation> {
    try {
      const res = await fetch(
        `${API_BASE_URL}/api/conversations/${encodeURIComponent(conversationId)}/summarize-title`,
        { method: "POST" }
      );
      if (!res.ok) {
        const errJson = await res.json().catch(() => ({}));
        throw new ApiError(res.status, sanitizeErrorMessage(res.status, errJson.detail));
      }
      return res.json();
    } catch (err: unknown) {
      if (err instanceof ApiError) throw err;
      throw new ApiError(0, sanitizeErrorMessage(0));
    }
  },

  /**
   * Delete a conversation and its messages.
   * Endpoint: DELETE /api/conversations/{conversationId}
   */
  async deleteConversation(conversationId: string): Promise<boolean> {
    try {
      const res = await fetch(
        `${API_BASE_URL}/api/conversations/${encodeURIComponent(conversationId)}`,
        { method: "DELETE" }
      );
      if (!res.ok && res.status !== 404) {
        const errJson = await res.json().catch(() => ({}));
        throw new ApiError(res.status, sanitizeErrorMessage(res.status, errJson.detail));
      }
      return true;
    } catch (err: unknown) {
      if (err instanceof ApiError) throw err;
      throw new ApiError(0, sanitizeErrorMessage(0));
    }
  },

  /**
   * Fetch all saved messages for a conversation.
   * Endpoint: GET /api/conversations/{conversationId}/messages
   */
  async getConversationMessages(
    conversationId: string
  ): Promise<import("./types").StoredMessage[]> {
    try {
      const res = await fetch(
        `${API_BASE_URL}/api/conversations/${encodeURIComponent(conversationId)}/messages`
      );
      if (!res.ok) {
        const errJson = await res.json().catch(() => ({}));
        throw new ApiError(res.status, sanitizeErrorMessage(res.status, errJson.detail));
      }
      return res.json();
    } catch (err: unknown) {
      if (err instanceof ApiError) throw err;
      throw new ApiError(0, sanitizeErrorMessage(0));
    }
  },

  /**
   * Perform semantic vector retrieval for a document without generating an LLM response.
   * Endpoint: POST /api/documents/{documentId}/search
   */
  async searchDocument(
    documentId: string,
    query: string,
    topK = 5,
    similarityThreshold?: number
  ): Promise<SearchResponse> {
    try {
      const res = await fetch(
        `${API_BASE_URL}/api/documents/${encodeURIComponent(documentId)}/search`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            query,
            top_k: topK,
            similarity_threshold: similarityThreshold,
          }),
        }
      );

      if (!res.ok) {
        const errJson = await res.json().catch(() => ({}));
        throw new ApiError(res.status, sanitizeErrorMessage(res.status, errJson.detail));
      }

      return res.json();
    } catch (err: unknown) {
      if (err instanceof ApiError) throw err;
      throw new ApiError(0, sanitizeErrorMessage(0));
    }
  },

  /**
   * Send a chat question to the grounded tutor layer (Nemotron 3 Nano 30B Cloud via Ollama Cloud).
   * Endpoint: POST /api/chat
   */
  async sendChatMessage(request: ChatRequest): Promise<ChatResponse> {
    if (!request.document_id) {
      throw new ApiError(400, "Please upload or select an active academic document first.");
    }
    if (!request.message || !request.message.trim()) {
      throw new ApiError(400, "Please enter a question for your tutor.");
    }

    try {
      const res = await fetch(`${API_BASE_URL}/api/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          document_id: request.document_id,
          message: request.message.trim(),
          mode: request.mode || "simple",
          conversation: request.conversation || [],
          top_k: request.top_k || 5,
          similarity_threshold: request.similarity_threshold,
          conversation_id: request.conversation_id,
        }),
      });

      if (!res.ok) {
        const errJson = await res.json().catch(() => ({}));
        throw new ApiError(res.status, sanitizeErrorMessage(res.status, errJson.detail));
      }

      return res.json();
    } catch (err: unknown) {
      if (err instanceof ApiError) throw err;
      throw new ApiError(0, sanitizeErrorMessage(0));
    }
  },

  /**
   * Generate or retrieve cached document summary.
   * Endpoint: POST /api/documents/{documentId}/summary
   */
  async getSummary(
    documentId: string,
    forceRegenerate = false,
    maxTopics = 8
  ): Promise<import("./types").SummaryResponse> {
    try {
      const res = await fetch(
        `${API_BASE_URL}/api/documents/${encodeURIComponent(documentId)}/summary`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            force_regenerate: forceRegenerate,
            max_topics: maxTopics,
          }),
        }
      );

      if (!res.ok) {
        const errJson = await res.json().catch(() => ({}));
        throw new ApiError(res.status, sanitizeErrorMessage(res.status, errJson.detail));
      }

      return res.json();
    } catch (err: unknown) {
      if (err instanceof ApiError) throw err;
      throw new ApiError(0, sanitizeErrorMessage(0));
    }
  },

  /**
   * Generate or retrieve cached revision notes.
   * Endpoint: POST /api/documents/{documentId}/notes
   */
  async getNotes(
    documentId: string,
    forceRegenerate = false
  ): Promise<import("./types").NotesResponse> {
    try {
      const res = await fetch(
        `${API_BASE_URL}/api/documents/${encodeURIComponent(documentId)}/notes`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            force_regenerate: forceRegenerate,
          }),
        }
      );

      if (!res.ok) {
        const errJson = await res.json().catch(() => ({}));
        throw new ApiError(res.status, sanitizeErrorMessage(res.status, errJson.detail));
      }

      return res.json();
    } catch (err: unknown) {
      if (err instanceof ApiError) throw err;
      throw new ApiError(0, sanitizeErrorMessage(0));
    }
  },

  /**
   * Generate or retrieve cached grounded MCQ quiz.
   * Endpoint: POST /api/documents/{documentId}/quiz
   */
  async getQuiz(
    documentId: string,
    numQuestions = 10,
    topic?: string,
    forceRegenerate = false
  ): Promise<import("./types").QuizResponse> {
    try {
      const res = await fetch(
        `${API_BASE_URL}/api/documents/${encodeURIComponent(documentId)}/quiz`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            num_questions: numQuestions,
            question_type: "mcq",
            topic: topic || null,
            force_regenerate: forceRegenerate,
          }),
        }
      );

      if (!res.ok) {
        const errJson = await res.json().catch(() => ({}));
        throw new ApiError(res.status, sanitizeErrorMessage(res.status, errJson.detail));
      }

      return res.json();
    } catch (err: unknown) {
      if (err instanceof ApiError) throw err;
      throw new ApiError(0, sanitizeErrorMessage(0));
    }
  },

  /**
   * Submit quiz answers to evaluate score and detect weak topics.
   * Endpoint: POST /api/documents/{documentId}/quiz/evaluate
   */
  async evaluateQuiz(
    documentId: string,
    answers: import("./types").UserAnswerSubmission[],
    questions: import("./types").QuizQuestion[]
  ): Promise<import("./types").QuizEvaluationResponse> {
    try {
      const res = await fetch(
        `${API_BASE_URL}/api/documents/${encodeURIComponent(documentId)}/quiz/evaluate`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            answers,
            questions,
          }),
        }
      );

      if (!res.ok) {
        const errJson = await res.json().catch(() => ({}));
        throw new ApiError(res.status, sanitizeErrorMessage(res.status, errJson.detail));
      }

      return res.json();
    } catch (err: unknown) {
      if (err instanceof ApiError) throw err;
      throw new ApiError(0, sanitizeErrorMessage(0));
    }
  },
};
