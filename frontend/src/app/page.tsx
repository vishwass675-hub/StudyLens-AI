"use client";

import React, { useState, useEffect, useRef, useCallback } from "react";
import {
  DocumentMetadata,
  ChatMessage,
  TutorMode,
  ActiveToolTab,
  Conversation,
} from "@/lib/types";
import { api, ApiError } from "@/lib/api";
import { Sidebar } from "@/components/layout/Sidebar";
import { PDFUploader } from "@/components/document/PDFUploader";
import { EmptyState } from "@/components/chat/EmptyState";
import { MessageItem } from "@/components/chat/MessageItem";
import { LoadingIndicator } from "@/components/chat/LoadingIndicator";
import { ChatComposer } from "@/components/chat/ChatComposer";
import { SummaryView } from "@/components/study/SummaryView";
import { NotesView } from "@/components/study/NotesView";
import { QuizView } from "@/components/study/QuizView";
import { ErrorBanner } from "@/components/ui/ErrorBanner";
import { SplashScreen } from "@/components/ui/SplashScreen";
import {
  Menu,
  FileText,
  MessageSquare,
  Bookmark,
  Award,
  Plus,
  ChevronDown,
} from "lucide-react";

function cleanDocTitle(filename: string): string {
  return filename.replace(/^\d+[-_]/, "");
}

export default function StudyLensApp() {
  const [activeDocument, setActiveDocument] = useState<DocumentMetadata | null>(null);
  const [documentsHistory, setDocumentsHistory] = useState<DocumentMetadata[]>([]);
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeConversationId, setActiveConversationId] = useState<string | null>(null);

  const [activeTab, setActiveTab] = useState<ActiveToolTab>("chat");
  const [quizTopic, setQuizTopic] = useState<string | null>(null);

  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [tutorMode, setTutorMode] = useState<TutorMode>("simple");
  const [isLoading, setIsLoading] = useState(false);
  const [isProcessingPDF, setIsProcessingPDF] = useState(false);
  const [isUploadOpen, setIsUploadOpen] = useState(false);
  const [showDocPicker, setShowDocPicker] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isBackendOnline, setIsBackendOnline] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(true);

  const chatBottomRef = useRef<HTMLDivElement>(null);

  // Auto-scroll on new message or loading change in chat view
  useEffect(() => {
    if (activeTab === "chat") {
      chatBottomRef.current?.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages, isLoading, activeTab]);

  // Load conversation messages helper
  const loadConversationMessages = useCallback(async (convId: string) => {
    try {
      const stored = await api.getConversationMessages(convId);
      const mapped: ChatMessage[] = stored.map((m) => ({
        id: m.id,
        role: m.role,
        content: m.content,
        sources: m.sources,
        timestamp: new Date(m.created_at).toLocaleTimeString([], {
          hour: "2-digit",
          minute: "2-digit",
        }),
      }));
      setMessages(mapped);
    } catch {
      setMessages([]);
    }
  }, []);

  // Fetch conversations for a specific document helper
  const refreshConversations = useCallback(
    async (docId: string, preferredConvId?: string) => {
      try {
        const convList = await api.listConversations(docId);
        setConversations(convList);

        if (convList.length > 0) {
          const target =
            convList.find((c) => c.id === preferredConvId) || convList[0];
          setActiveConversationId(target.id);
          try {
            localStorage.setItem("studylens_active_conv_id", target.id);
          } catch {}
          await loadConversationMessages(target.id);
        } else {
          setActiveConversationId(null);
          setMessages([]);
          try {
            localStorage.removeItem("studylens_active_conv_id");
          } catch {}
        }
      } catch {
        setConversations([]);
        setActiveConversationId(null);
        setMessages([]);
      }
    },
    [loadConversationMessages]
  );

  // Initial health check and document library fetch
  useEffect(() => {
    const initializeApp = async () => {
      const online = await api.checkHealth();
      setIsBackendOnline(online);
      if (!online) return;

      const docs = await api.listDocuments();
      if (!docs || docs.length === 0) {
        setDocumentsHistory([]);
        setActiveDocument(null);
        setConversations([]);
        setActiveConversationId(null);
        setMessages([]);
        return;
      }

      setDocumentsHistory(docs);

      // Restore active document from localStorage if valid
      let savedDocId: string | null = null;
      let savedConvId: string | null = null;
      try {
        savedDocId = localStorage.getItem("studylens_active_doc_id");
        savedConvId = localStorage.getItem("studylens_active_conv_id");
      } catch {}

      const initialDoc =
        (savedDocId ? docs.find((d) => d.document_id === savedDocId) : null) ||
        docs.find((d) => d.status === "ready") ||
        docs[0];

      setActiveDocument(initialDoc);
      try {
        localStorage.setItem("studylens_active_doc_id", initialDoc.document_id);
      } catch {}

      await refreshConversations(initialDoc.document_id, savedConvId || undefined);
    };

    initializeApp();
    const interval = setInterval(async () => {
      const online = await api.checkHealth();
      setIsBackendOnline(online);
    }, 10000);
    return () => clearInterval(interval);
  }, [refreshConversations]);

  // Upload a new PDF
  const handleUploadPDF = async (file: File): Promise<DocumentMetadata> => {
    setIsProcessingPDF(true);
    setErrorMessage(null);
    try {
      const doc = await api.uploadDocument(file);
      setActiveDocument(doc);
      setDocumentsHistory((prev) => [
        doc,
        ...prev.filter((d) => d.document_id !== doc.document_id),
      ]);
      try {
        localStorage.setItem("studylens_active_doc_id", doc.document_id);
      } catch {}

      // Create initial conversation for the new document
      const initialConv = await api.createConversation(doc.document_id, "New Chat");
      setConversations([initialConv]);
      setActiveConversationId(initialConv.id);
      try {
        localStorage.setItem("studylens_active_conv_id", initialConv.id);
      } catch {}

      setMessages([]);
      setActiveTab("chat");
      return doc;
    } catch (err: unknown) {
      const msg =
        err instanceof ApiError
          ? err.message
          : "We couldn't process this document. Please try uploading it again.";
      setErrorMessage(msg);
      throw err;
    } finally {
      setIsProcessingPDF(false);
    }
  };

  // Switch to another document
  const handleSelectDocument = async (doc: DocumentMetadata) => {
    if (activeDocument?.document_id === doc.document_id) return;
    setActiveDocument(doc);
    setErrorMessage(null);
    setActiveTab("chat");
    try {
      localStorage.setItem("studylens_active_doc_id", doc.document_id);
    } catch {}
    await refreshConversations(doc.document_id);
  };

  // Reset active document
  const handleResetDocument = () => {
    setActiveDocument(null);
    setConversations([]);
    setActiveConversationId(null);
    setMessages([]);
    setErrorMessage(null);
    setActiveTab("chat");
    try {
      localStorage.removeItem("studylens_active_doc_id");
      localStorage.removeItem("studylens_active_conv_id");
    } catch {}
  };

  // Delete document
  const handleDeleteDocument = async (docId: string) => {
    try {
      await api.deleteDocument(docId);
      const remainingDocs = documentsHistory.filter(
        (d) => d.document_id !== docId
      );
      setDocumentsHistory(remainingDocs);

      if (activeDocument?.document_id === docId) {
        if (remainingDocs.length > 0) {
          const nextDoc = remainingDocs[0];
          setActiveDocument(nextDoc);
          try {
            localStorage.setItem("studylens_active_doc_id", nextDoc.document_id);
          } catch {}
          await refreshConversations(nextDoc.document_id);
        } else {
          handleResetDocument();
        }
      }
    } catch (err: unknown) {
      const msg =
        err instanceof ApiError ? err.message : "Failed to delete document.";
      setErrorMessage(msg);
    }
  };

  // Select an existing conversation
  const handleSelectConversation = async (convId: string) => {
    // If the conversation belongs to a different document, switch active document
    const targetConv = conversations.find((c) => c.id === convId);
    if (targetConv && targetConv.document_id !== activeDocument?.document_id) {
      const targetDoc = documentsHistory.find(
        (d) => d.document_id === targetConv.document_id
      );
      if (targetDoc) {
        setActiveDocument(targetDoc);
        try {
          localStorage.setItem("studylens_active_doc_id", targetDoc.document_id);
        } catch {}
      }
    }
    setActiveConversationId(convId);
    try {
      localStorage.setItem("studylens_active_conv_id", convId);
    } catch {}
    await loadConversationMessages(convId);
    if (activeTab !== "chat") {
      setActiveTab("chat");
    }
  };

  // Start a new chat session with a new document ("new chat = new doc")
  const handleNewConversation = () => {
    setActiveDocument(null);
    setConversations([]);
    setActiveConversationId(null);
    setMessages([]);
    setErrorMessage(null);
    setActiveTab("chat");
    try {
      localStorage.removeItem("studylens_active_doc_id");
      localStorage.removeItem("studylens_active_conv_id");
    } catch {}
    setIsUploadOpen(true);
  };

  // Rename a conversation
  const handleRenameConversation = async (convId: string, newTitle: string) => {
    try {
      const updated = await api.updateConversationTitle(convId, newTitle);
      setConversations((prev) =>
        prev.map((c) => (c.id === convId ? updated : c))
      );
    } catch (err: unknown) {
      const msg =
        err instanceof ApiError ? err.message : "Failed to rename conversation.";
      setErrorMessage(msg);
    }
  };

  // Delete a conversation
  const handleDeleteConversation = async (convId: string) => {
    try {
      await api.deleteConversation(convId);
      const remaining = conversations.filter((c) => c.id !== convId);
      setConversations(remaining);

      if (activeConversationId === convId) {
        if (remaining.length > 0) {
          const nextConv = remaining[0];
          setActiveConversationId(nextConv.id);
          try {
            localStorage.setItem("studylens_active_conv_id", nextConv.id);
          } catch {}
          await loadConversationMessages(nextConv.id);
        } else {
          setActiveConversationId(null);
          setMessages([]);
          try {
            localStorage.removeItem("studylens_active_conv_id");
          } catch {}
        }
      }
    } catch (err: unknown) {
      const msg =
        err instanceof ApiError ? err.message : "Failed to delete conversation.";
      setErrorMessage(msg);
    }
  };

  // Send chat message
  const handleSendMessage = async (
    questionText: string,
    overrideMode?: TutorMode
  ) => {
    if (!questionText.trim()) return;

    if (!activeDocument) {
      setErrorMessage("Please upload or select an academic PDF first.");
      return;
    }

    if (activeDocument.status !== "ready") {
      setErrorMessage(
        "The document is still being indexed. Please wait until it is ready."
      );
      return;
    }

    setErrorMessage(null);

    const userMsg: ChatMessage = {
      id: `user_${Date.now()}`,
      role: "user",
      content: questionText,
      timestamp: new Date().toLocaleTimeString([], {
        hour: "2-digit",
        minute: "2-digit",
      }),
    };

    const newHistory = [...messages, userMsg];
    setMessages(newHistory);
    setIsLoading(true);

    if (activeTab !== "chat") {
      setActiveTab("chat");
    }

    // Build bounded conversation context turns (last 6 messages)
    const conversationContext = messages.slice(-6).map((m) => ({
      role: m.role,
      content: m.content,
    }));

    try {
      const response = await api.sendChatMessage({
        document_id: activeDocument.document_id,
        message: questionText,
        mode: overrideMode || tutorMode,
        conversation: conversationContext,
        conversation_id: activeConversationId || undefined,
      });

      const assistantMsg: ChatMessage = {
        id: `asst_${Date.now()}`,
        role: "assistant",
        content: response.answer,
        sources: response.sources,
        timestamp: new Date().toLocaleTimeString([], {
          hour: "2-digit",
          minute: "2-digit",
        }),
      };

      setMessages([...newHistory, assistantMsg]);

      // If backend assigned or returned a conversation_id, ensure active state and refresh titles
      if (response.conversation_id) {
        if (response.conversation_id !== activeConversationId) {
          setActiveConversationId(response.conversation_id);
          try {
            localStorage.setItem(
              "studylens_active_conv_id",
              response.conversation_id
            );
          } catch {}
        }
        // Refresh conversations in background to reflect auto-generated title
        api.listConversations(activeDocument.document_id).then(setConversations);
      }
    } catch (err: unknown) {
      const errorText =
        err instanceof ApiError
          ? err.message
          : !isBackendOnline
          ? "Unable to reach the StudyLens backend. Please ensure the server is running on http://127.0.0.1:8000."
          : "An error occurred while generating your tutor explanation. Please try again.";
      setErrorMessage(errorText);

      setMessages([
        ...newHistory,
        {
          id: `err_${Date.now()}`,
          role: "assistant",
          content: errorText,
          sources: [],
          isError: true,
          timestamp: new Date().toLocaleTimeString([], {
            hour: "2-digit",
            minute: "2-digit",
          }),
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  // Quick action dispatch
  const handleQuickAction = (
    actionType: "simpler" | "example" | "exam" | "quiz"
  ) => {
    if (actionType === "simpler") {
      handleSendMessage(
        "Could you please explain your previous answer in simpler terms using an everyday analogy?",
        "eli5"
      );
    } else if (actionType === "example") {
      handleSendMessage(
        "Could you provide a concrete example directly from the document illustrating your previous explanation?"
      );
    } else if (actionType === "exam") {
      handleSendMessage(
        "Could you convert your previous answer into a concise, high-scoring exam preparation answer with key bullet points?",
        "exam"
      );
    } else if (actionType === "quiz") {
      setQuizTopic(null);
      setActiveTab("quiz");
    }
  };

  const isDocReady = activeDocument?.status === "ready";

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-white text-black font-sans">
      {/* Animated Brand Splash Screen */}
      <SplashScreen isReady={isBackendOnline} />

      {/* Sidebar with Document Library & Conversation History */}
      <Sidebar
        activeDocument={activeDocument}
        documentsHistory={documentsHistory}
        activeConversationId={activeConversationId}
        conversations={conversations}
        onOpenUpload={() => setIsUploadOpen(true)}
        onResetDocument={handleResetDocument}
        onSelectDocument={handleSelectDocument}
        onDeleteDocument={handleDeleteDocument}
        onSelectConversation={handleSelectConversation}
        onNewConversation={handleNewConversation}
        onRenameConversation={handleRenameConversation}
        onDeleteConversation={handleDeleteConversation}
        isBackendOnline={isBackendOnline}
        isOpen={sidebarOpen}
        onToggle={() => setSidebarOpen(!sidebarOpen)}
      />

      {/* Main Workstation */}
      <div className="flex-1 flex flex-col h-full min-w-0 relative bg-white overflow-hidden">
        {/* Top Header & Study Tool Tabs Bar */}
        <header className="h-14 border-b border-zinc-200 px-4 sm:px-6 flex items-center justify-between shrink-0 bg-white z-10 gap-3">
          {/* Left: Brand & Document Selector */}
          <div className="flex items-center gap-2.5 min-w-0">
            {!sidebarOpen && (
              <button
                onClick={() => setSidebarOpen(true)}
                className="p-1.5 rounded-lg text-zinc-500 hover:text-black hover:bg-zinc-100 transition-colors cursor-pointer shrink-0"
                title="Open sidebar"
              >
                <Menu className="w-5 h-5" />
              </button>
            )}

            <span className="font-bold text-sm text-black tracking-tight shrink-0">
              StudyLens AI
            </span>

            {activeDocument && (
              <>
                <span className="text-zinc-300 hidden sm:inline select-none">/</span>
                <div className="relative min-w-0">
                  <button
                    onClick={() => setShowDocPicker(!showDocPicker)}
                    className="flex items-center gap-1.5 bg-zinc-50 hover:bg-zinc-100 text-zinc-900 text-xs px-2.5 py-1 rounded-lg font-medium border border-zinc-200 max-w-[140px] sm:max-w-[180px] md:max-w-[220px] transition-colors cursor-pointer"
                    title={documentsHistory.length > 1 ? "Click to switch document" : activeDocument.filename}
                  >
                    <FileText className="w-3.5 h-3.5 text-zinc-500 shrink-0" />
                    <span className="truncate">{cleanDocTitle(activeDocument.filename)}</span>
                    <span className="text-zinc-400 font-normal shrink-0 text-[11px]">
                      · {activeDocument.page_count || activeDocument.total_pages || 1}p
                    </span>
                    {documentsHistory.length > 1 && (
                      <ChevronDown className="w-3 h-3 text-zinc-400 shrink-0" />
                    )}
                  </button>

                  {showDocPicker && documentsHistory.length > 1 && (
                    <div className="absolute top-full left-0 mt-1.5 w-64 bg-white border border-zinc-200 rounded-xl shadow-lg p-1.5 z-50 animate-in fade-in duration-100">
                      <div className="text-[10px] font-bold text-zinc-400 uppercase tracking-wider px-2 py-1">
                        Saved Documents
                      </div>
                      <div className="max-h-48 overflow-y-auto space-y-0.5">
                        {documentsHistory.map((d) => (
                          <button
                            key={d.document_id}
                            onClick={() => {
                              handleSelectDocument(d);
                              setShowDocPicker(false);
                            }}
                            className={`w-full text-left px-2 py-1.5 rounded-lg text-xs truncate flex items-center justify-between transition-colors cursor-pointer ${
                              d.document_id === activeDocument.document_id
                                ? "bg-black text-white font-semibold"
                                : "hover:bg-zinc-100 text-zinc-800"
                            }`}
                          >
                            <span className="truncate">{cleanDocTitle(d.filename)}</span>
                            <span
                              className={`text-[10px] ${
                                d.document_id === activeDocument.document_id
                                  ? "text-zinc-300"
                                  : "text-zinc-400"
                              }`}
                            >
                              {d.page_count || d.total_pages}p
                            </span>
                          </button>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </>
            )}
          </div>

          {/* Center: Tool Navigation Tabs */}
          <div className="flex items-center gap-1 bg-zinc-100 p-1 rounded-xl border border-zinc-200 text-xs shrink-0">
            <button
              onClick={() => setActiveTab("chat")}
              className={`px-3 py-1 rounded-lg font-medium transition-all duration-200 flex items-center gap-1.5 cursor-pointer hover:scale-[1.02] active:scale-[0.98] ${
                activeTab === "chat"
                  ? "bg-black text-white font-semibold shadow-xs"
                  : "text-zinc-600 hover:text-black hover:bg-zinc-200/50"
              }`}
            >
              <MessageSquare className="w-3.5 h-3.5" />
              <span>Chat</span>
            </button>

            <button
              onClick={() => isDocReady && setActiveTab("summary")}
              disabled={!isDocReady}
              className={`px-3 py-1 rounded-lg font-medium transition-all duration-200 flex items-center gap-1.5 ${
                !isDocReady
                  ? "text-zinc-400 opacity-60 cursor-not-allowed"
                  : activeTab === "summary"
                  ? "bg-black text-white font-semibold shadow-xs cursor-pointer hover:scale-[1.02] active:scale-[0.98]"
                  : "text-zinc-600 hover:text-black hover:bg-zinc-200/50 cursor-pointer hover:scale-[1.02] active:scale-[0.98]"
              }`}
              title={
                isDocReady
                  ? "View structured document summary"
                  : "Upload a PDF to activate summary"
              }
            >
              <FileText className="w-3.5 h-3.5" />
              <span>Summary</span>
            </button>

            <button
              onClick={() => isDocReady && setActiveTab("notes")}
              disabled={!isDocReady}
              className={`px-3 py-1 rounded-lg font-medium transition-all duration-200 flex items-center gap-1.5 ${
                !isDocReady
                  ? "text-zinc-400 opacity-60 cursor-not-allowed"
                  : activeTab === "notes"
                  ? "bg-black text-white font-semibold shadow-xs cursor-pointer hover:scale-[1.02] active:scale-[0.98]"
                  : "text-zinc-600 hover:text-black hover:bg-zinc-200/50 cursor-pointer hover:scale-[1.02] active:scale-[0.98]"
              }`}
              title={
                isDocReady
                  ? "View revision study notes"
                  : "Upload a PDF to activate notes"
              }
            >
              <Bookmark className="w-3.5 h-3.5" />
              <span>Notes</span>
            </button>

            <button
              onClick={() => isDocReady && setActiveTab("quiz")}
              disabled={!isDocReady}
              className={`px-3 py-1 rounded-lg font-medium transition-all duration-200 flex items-center gap-1.5 ${
                !isDocReady
                  ? "text-zinc-400 opacity-60 cursor-not-allowed"
                  : activeTab === "quiz"
                  ? "bg-black text-white font-semibold shadow-xs cursor-pointer hover:scale-[1.02] active:scale-[0.98]"
                  : "text-zinc-600 hover:text-black hover:bg-zinc-200/50 cursor-pointer hover:scale-[1.02] active:scale-[0.98]"
              }`}
              title={
                isDocReady
                  ? "Take interactive grounded quiz"
                  : "Upload a PDF to activate quiz"
              }
            >
              <Award className="w-3.5 h-3.5" />
              <span>Quiz</span>
            </button>
          </div>

          {/* Right: Actions */}
          <div className="flex items-center gap-2 shrink-0">
            <button
              onClick={() => setIsUploadOpen(true)}
              className="px-3.5 py-1.5 bg-black hover:bg-zinc-800 text-white font-semibold rounded-xl text-xs transition-all cursor-pointer flex items-center gap-1.5 shadow-xs hover:scale-[1.02] active:scale-[0.98]"
            >
              <Plus className="w-3.5 h-3.5 stroke-[2.5]" />
              <span>Upload File</span>
            </button>
          </div>
        </header>

        {/* Global Error Notice Banner */}
        {errorMessage && (
          <div className="px-4 max-w-3xl mx-auto w-full pt-3">
            <ErrorBanner
              message={errorMessage}
              onDismiss={() => setErrorMessage(null)}
              onRetry={
                !isBackendOnline
                  ? () => api.checkHealth().then(setIsBackendOnline)
                  : undefined
              }
            />
          </div>
        )}

        {/* Active Tool View Content */}
        {activeTab === "summary" && (
          <SummaryView document={activeDocument} />
        )}

        {activeTab === "notes" && (
          <NotesView document={activeDocument} />
        )}

        {activeTab === "quiz" && (
          <QuizView document={activeDocument} initialTopic={quizTopic} />
        )}

        {activeTab === "chat" && (
          <>
            {/* Chat Content Container */}
            <div
              className={`flex-1 flex flex-col ${
                !activeDocument || messages.length === 0
                  ? "overflow-hidden"
                  : "overflow-y-auto"
              }`}
            >
              {messages.length === 0 ? (
                <EmptyState
                  document={activeDocument}
                  onOpenUpload={() => setIsUploadOpen(true)}
                  onSelectPrompt={handleSendMessage}
                />
              ) : (
                <div className="flex-1 divide-y divide-zinc-100 pb-6">
                  {messages.map((msg) => (
                    <MessageItem
                      key={msg.id}
                      message={msg}
                      onQuickAction={handleQuickAction}
                    />
                  ))}

                  {isLoading && <LoadingIndicator />}
                  <div ref={chatBottomRef} />
                </div>
              )}
            </div>

            {/* Chat Composer - only shown when a document is active */}
            {activeDocument && (
              <ChatComposer
                document={activeDocument}
                isLoading={isLoading}
                tutorMode={tutorMode}
                onChangeTutorMode={setTutorMode}
                onSendMessage={handleSendMessage}
                onClearChat={() => setMessages([])}
                hasMessages={messages.length > 0}
              />
            )}
          </>
        )}
      </div>

      {/* PDF Upload Modal */}
      <PDFUploader
        isOpen={isUploadOpen}
        onClose={() => setIsUploadOpen(false)}
        onUpload={handleUploadPDF}
        isProcessing={isProcessingPDF}
      />
    </div>
  );
}
