export type TutorMode = "simple" | "detailed" | "exam" | "eli5";

export type DocumentStatus = "uploaded" | "processing" | "ready" | "failed";

export type ActiveToolTab = "chat" | "summary" | "notes" | "quiz";

export interface SourceReference {
  document: string;
  page: number;
}

export interface DocumentMetadata {
  document_id: string;
  filename: string;
  page_count: number;
  status: DocumentStatus;
  total_words?: number;
  total_chars?: number;
  total_chunks?: number;
  error_message?: string | null;
  created_at?: string;
  updated_at?: string;
  last_accessed_at?: string;
  total_pages?: number;
}

export interface ConversationMessage {
  role: "user" | "assistant";
  content: string;
}

export interface StoredMessage {
  id: string;
  conversation_id: string;
  role: "user" | "assistant";
  content: string;
  sources?: SourceReference[];
  created_at: string;
}

export interface Conversation {
  id: string;
  document_id: string;
  document_filename?: string | null;
  title: string;
  created_at: string;
  updated_at: string;
  message_count?: number;
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  sources?: SourceReference[];
  timestamp?: string;
  isError?: boolean;
}

export interface ChatRequest {
  document_id: string;
  message: string;
  mode: TutorMode;
  conversation?: ConversationMessage[];
  top_k?: number;
  similarity_threshold?: number;
  conversation_id?: string;
}

export interface ChatResponse {
  answer: string;
  sources: SourceReference[];
  conversation_id?: string;
}

export interface SearchRequest {
  query: string;
  top_k?: number;
  similarity_threshold?: number;
}

export interface SearchResultItem {
  chunk_id: string;
  document_id: string;
  page: number;
  filename: string;
  text: string;
  score: number;
  metadata?: Record<string, unknown>;
}

export interface SearchResponse {
  document_id: string;
  query: string;
  relevant_found: boolean;
  results_count: number;
  results: SearchResultItem[];
  message: string;
}

// -----------------------------------------------------------------------------
// Study Tools Contracts
// -----------------------------------------------------------------------------
export interface DefinitionItem {
  term: string;
  definition: string;
}

export interface SummaryResponse {
  document_id: string;
  document_overview: string;
  topics: string[];
  key_takeaways: string[];
  key_definitions: DefinitionItem[];
  exam_points: string[];
  sources: SourceReference[];
  cached?: boolean;
}

export interface NoteSection {
  heading: string;
  summary: string;
  key_points: string[];
  exam_tip?: string | null;
}

export interface NotesResponse {
  document_id: string;
  title: string;
  markdown_content: string;
  sections: NoteSection[];
  sources: SourceReference[];
  cached?: boolean;
}

export interface QuizQuestion {
  id: number;
  topic: string;
  question: string;
  options: string[];
  correct_answer: string;
  explanation: string;
  page_hint?: number | null;
}

export interface QuizResponse {
  document_id: string;
  quiz_id: string;
  total_questions: number;
  questions: QuizQuestion[];
  sources: SourceReference[];
  cached?: boolean;
}

export interface UserAnswerSubmission {
  question_id: number;
  user_answer: string;
  topic: string;
}

export interface WeakTopicItem {
  topic: string;
  incorrect: number;
  total: number;
  accuracy_percentage: number;
}

export interface QuizEvaluationResponse {
  score: number;
  total: number;
  accuracy_percentage: number;
  weak_topics: WeakTopicItem[];
  recommendations: string[];
}
