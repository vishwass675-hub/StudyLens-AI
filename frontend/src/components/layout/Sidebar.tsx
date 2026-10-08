import React, { useState } from "react";
import { DocumentMetadata, Conversation } from "@/lib/types";
import { api } from "@/lib/api";
import {
  GraduationCap,
  Plus,
  FileText,
  RotateCcw,
  Sliders,
  ChevronLeft,
  ChevronRight,
  Database,
  Cpu,
  CheckCircle2,
  XCircle,
  ShieldCheck,
  Trash2,
  Edit2,
  MessageSquare,
  Clock,
  Calendar,
  AlertTriangle,
  FolderOpen,
  Download,
  Sparkles,
} from "lucide-react";

interface SidebarProps {
  activeDocument: DocumentMetadata | null;
  documentsHistory: DocumentMetadata[];
  activeConversationId: string | null;
  conversations: Conversation[];
  onOpenUpload?: () => void;
  onResetDocument: () => void;
  onSelectDocument: (doc: DocumentMetadata) => void;
  onDeleteDocument: (docId: string) => Promise<void>;
  onSelectConversation: (convId: string) => void;
  onNewConversation: () => void;
  onRenameConversation: (convId: string, newTitle: string) => Promise<void>;
  onDeleteConversation: (convId: string) => Promise<void>;
  isBackendOnline: boolean;
  isOpen: boolean;
  onToggle: () => void;
}

const docColorThemes = [
  { bg: "bg-zinc-100", text: "text-black", border: "border-zinc-200" },
  { bg: "bg-zinc-100", text: "text-zinc-800", border: "border-zinc-200" },
  { bg: "bg-zinc-100", text: "text-zinc-900", border: "border-zinc-200" },
];

function formatDate(isoString?: string): string {
  if (!isoString) return "Recently";
  try {
    const d = new Date(isoString);
    if (isNaN(d.getTime())) return "Recently";
    return d.toLocaleDateString([], { month: "short", day: "numeric" });
  } catch {
    return "Recently";
  }
}

function formatTime(isoString?: string): string {
  if (!isoString) return "";
  try {
    const d = new Date(isoString);
    if (isNaN(d.getTime())) return "";
    return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  } catch {
    return "";
  }
}

function cleanDocTitle(filename: string): string {
  return filename.replace(/^\d+[-_]/, "");
}

export const Sidebar: React.FC<SidebarProps> = ({
  activeDocument,
  documentsHistory,
  activeConversationId,
  conversations,
  onOpenUpload,
  onResetDocument,
  onSelectDocument,
  onDeleteDocument,
  onSelectConversation,
  onNewConversation,
  onRenameConversation,
  onDeleteConversation,
  isBackendOnline,
  isOpen,
  onToggle,
}) => {
  const [showSettings, setShowSettings] = useState(false);
  const [activeView, setActiveView] = useState<"all" | "docs" | "chats">("all");

  // Deletion Confirmation Modal State
  const [docToDelete, setDocToDelete] = useState<DocumentMetadata | null>(null);
  const [convToDelete, setConvToDelete] = useState<Conversation | null>(null);

  // Rename Conversation Modal State
  const [convToRename, setConvToRename] = useState<Conversation | null>(null);
  const [renameInput, setRenameInput] = useState("");

  const handleStartRename = (e: React.MouseEvent, conv: Conversation) => {
    e.stopPropagation();
    setConvToRename(conv);
    setRenameInput(conv.title);
  };

  const handleConfirmRename = async () => {
    if (convToRename && renameInput.trim()) {
      await onRenameConversation(convToRename.id, renameInput.trim());
      setConvToRename(null);
      setRenameInput("");
    }
  };

  const handleAutoSummarize = async (e: React.MouseEvent, conv: Conversation) => {
    e.stopPropagation();
    try {
      const updated = await api.summarizeConversationTitle(conv.id);
      await onRenameConversation(conv.id, updated.title);
    } catch {}
  };

  const handleConfirmDeleteDoc = async () => {
    if (docToDelete) {
      await onDeleteDocument(docToDelete.document_id);
      setDocToDelete(null);
    }
  };

  const handleConfirmDeleteConv = async () => {
    if (convToDelete) {
      await onDeleteConversation(convToDelete.id);
      setConvToDelete(null);
    }
  };

  return (
    <>
      {/* Mobile Overlay */}
      {isOpen && (
        <div
          onClick={onToggle}
          className="fixed inset-0 bg-black/40 z-30 md:hidden"
        />
      )}

      {/* Confirmation Modal for Document Deletion */}
      {docToDelete && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
          <div className="bg-white rounded-2xl max-w-sm w-full p-5 shadow-xl border border-zinc-200 animate-in fade-in duration-150">
            <div className="w-10 h-10 rounded-xl bg-zinc-100 text-black flex items-center justify-center mb-3">
              <AlertTriangle className="w-5 h-5" />
            </div>
            <h3 className="text-sm font-bold text-black">Delete Document?</h3>
            <p className="text-xs text-zinc-600 mt-1 leading-relaxed">
              Are you sure you want to delete{" "}
              <strong className="text-black">{docToDelete.filename}</strong>? This will permanently remove its embeddings, chat history, and study notes.
            </p>
            <div className="flex items-center justify-end gap-2 mt-5">
              <button
                onClick={() => setDocToDelete(null)}
                className="px-3 py-1.5 text-xs font-semibold text-zinc-600 hover:bg-zinc-100 rounded-lg transition-colors cursor-pointer"
              >
                Cancel
              </button>
              <button
                onClick={handleConfirmDeleteDoc}
                className="px-3.5 py-1.5 text-xs font-semibold bg-black hover:bg-zinc-800 text-white rounded-lg transition-colors cursor-pointer shadow-xs"
              >
                Delete Document
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Confirmation Modal for Conversation Deletion */}
      {convToDelete && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
          <div className="bg-white rounded-2xl max-w-sm w-full p-5 shadow-xl border border-zinc-200 animate-in fade-in duration-150">
            <div className="w-10 h-10 rounded-xl bg-zinc-100 text-black flex items-center justify-center mb-3">
              <Trash2 className="w-5 h-5" />
            </div>
            <h3 className="text-sm font-bold text-black">Delete Conversation?</h3>
            <p className="text-xs text-zinc-600 mt-1 leading-relaxed">
              Delete &quot;{convToDelete.title}&quot; and all of its messages? This action cannot be undone.
            </p>
            <div className="flex items-center justify-end gap-2 mt-5">
              <button
                onClick={() => setConvToDelete(null)}
                className="px-3 py-1.5 text-xs font-semibold text-zinc-600 hover:bg-zinc-100 rounded-lg transition-colors cursor-pointer"
              >
                Cancel
              </button>
              <button
                onClick={handleConfirmDeleteConv}
                className="px-3.5 py-1.5 text-xs font-semibold bg-black hover:bg-zinc-800 text-white rounded-lg transition-colors cursor-pointer shadow-xs"
              >
                Delete Chat
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Rename Conversation Modal */}
      {convToRename && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
          <div className="bg-white rounded-2xl max-w-sm w-full p-5 shadow-xl border border-zinc-200 animate-in fade-in duration-150">
            <h3 className="text-sm font-bold text-black">Rename Conversation</h3>
            <input
              type="text"
              value={renameInput}
              onChange={(e) => setRenameInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleConfirmRename()}
              placeholder="Conversation title"
              className="w-full mt-3 px-3 py-2 text-xs border border-zinc-300 rounded-lg focus:outline-none focus:ring-1 focus:ring-black focus:border-black"
              autoFocus
            />
            <div className="flex items-center justify-between gap-2 mt-4">
              <button
                type="button"
                onClick={async () => {
                  try {
                    const updated = await api.summarizeConversationTitle(convToRename.id);
                    setRenameInput(updated.title);
                  } catch {}
                }}
                className="text-xs text-zinc-600 hover:text-black flex items-center gap-1 cursor-pointer font-medium hover:underline"
                title="Automatically summarize what was texted in this chat into a title"
              >
                <Sparkles className="w-3 h-3 text-black" />
                <span>Auto-Summarize</span>
              </button>

              <div className="flex items-center gap-2">
                <button
                  onClick={() => setConvToRename(null)}
                  className="px-3 py-1.5 text-xs font-semibold text-zinc-600 hover:bg-zinc-100 rounded-lg transition-colors cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  onClick={handleConfirmRename}
                  className="px-3.5 py-1.5 text-xs font-semibold bg-black hover:bg-zinc-800 text-white rounded-lg transition-colors cursor-pointer shadow-xs"
                >
                  Save Title
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      <aside
        className={`fixed md:static inset-y-0 left-0 z-40 bg-white border-r border-zinc-200 flex flex-col transition-all duration-200 ease-in-out ${
          isOpen ? "w-80" : "w-0 md:w-16 overflow-hidden"
        }`}
      >
        {/* Sidebar Header */}
        <div className="h-14 px-4 border-b border-zinc-200 flex items-center justify-between shrink-0">
          <div className={`flex items-center gap-2.5 ${!isOpen && "md:hidden"}`}>
            <div className="w-8 h-8 rounded-xl bg-black text-white flex items-center justify-center shrink-0 border border-zinc-800">
              <GraduationCap className="w-4 h-4" />
            </div>
            <div>
              <div className="text-xs font-bold text-black tracking-tight leading-tight">
                StudyLens AI
              </div>
              <div className="text-[10px] text-zinc-500 font-medium">
                Academic AI Tutor
              </div>
            </div>
          </div>

          <button
            onClick={onToggle}
            className="p-1.5 rounded-lg text-zinc-400 hover:text-black hover:bg-zinc-100 transition-colors cursor-pointer"
            title={isOpen ? "Collapse sidebar" : "Expand sidebar"}
          >
            {isOpen ? <ChevronLeft className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
          </button>
        </div>

        {isOpen ? (
          <div className="flex-1 overflow-y-auto p-3 flex flex-col justify-between">
            <div className="space-y-4">
              {/* View Switcher Pills */}
              <div className="flex items-center gap-1 bg-zinc-100 p-1 rounded-xl text-[11px] font-semibold text-zinc-600">
                <button
                  onClick={() => setActiveView("all")}
                  className={`flex-1 py-1 text-center rounded-lg transition-all cursor-pointer ${
                    activeView === "all"
                      ? "bg-black text-white font-semibold shadow-xs"
                      : "hover:text-black"
                  }`}
                >
                  Overview
                </button>
                <button
                  onClick={() => setActiveView("docs")}
                  className={`flex-1 py-1 text-center rounded-lg transition-all cursor-pointer ${
                    activeView === "docs"
                      ? "bg-black text-white font-semibold shadow-xs"
                      : "hover:text-black"
                  }`}
                >
                  Documents ({documentsHistory.length})
                </button>
                <button
                  onClick={() => setActiveView("chats")}
                  className={`flex-1 py-1 text-center rounded-lg transition-all cursor-pointer ${
                    activeView === "chats"
                      ? "bg-black text-white font-semibold shadow-xs"
                      : "hover:text-black"
                  }`}
                >
                  Chats ({conversations.length})
                </button>
              </div>

              {/* SECTION 1: MY DOCUMENTS */}
              {(activeView === "all" || activeView === "docs") && (
                <div>
                  <div className="text-[10px] font-bold text-zinc-400 uppercase tracking-wider px-1 mb-2 flex items-center justify-between">
                    <span className="flex items-center gap-1">
                      <FolderOpen className="w-3 h-3 text-zinc-400" />
                      MY DOCUMENTS ({documentsHistory.length})
                    </span>
                    {activeDocument && (
                      <button
                        onClick={onResetDocument}
                        className="text-zinc-400 hover:text-black transition-colors flex items-center gap-0.5 text-[10px] font-medium"
                        title="Clear current selection"
                      >
                        <RotateCcw className="w-2.5 h-2.5" />
                        Reset
                      </button>
                    )}
                  </div>

                  {documentsHistory.length === 0 ? (
                    <div className="p-4 text-xs text-zinc-500 border border-dashed border-zinc-200 rounded-xl text-center bg-zinc-50 space-y-2 animate-fade-in">
                      <div className="w-9 h-9 rounded-xl bg-zinc-100 text-zinc-400 flex items-center justify-center mx-auto">
                        <FolderOpen className="w-4 h-4" />
                      </div>
                      <div className="font-semibold text-zinc-700">No documents yet</div>
                      <div className="text-[11px] text-zinc-400">
                        Upload your first study PDF to start learning.
                      </div>
                    </div>
                  ) : (
                    <div className="space-y-1.5">
                      {documentsHistory.map((doc, idx) => {
                        const isCurrent = activeDocument?.document_id === doc.document_id;
                        const theme = docColorThemes[idx % docColorThemes.length];
                        return (
                          <div
                            key={doc.document_id}
                            onClick={() => onSelectDocument(doc)}
                            className={`group relative p-2.5 rounded-xl border transition-all duration-200 cursor-pointer hover-lift active:scale-[0.99] ${
                              isCurrent
                                ? "bg-zinc-100 border-zinc-400 shadow-2xs"
                                : "bg-white hover:bg-zinc-50 border-zinc-200 hover:border-zinc-300"
                            }`}
                          >
                            <div className="flex items-start justify-between gap-2">
                              <div className="flex items-start gap-2.5 min-w-0 flex-1">
                                <div
                                  className={`w-7 h-7 rounded-lg ${theme.bg} ${theme.text} ${theme.border} border flex items-center justify-center shrink-0 mt-0.5 transition-transform group-hover:scale-105`}
                                >
                                  <FileText className="w-3.5 h-3.5" />
                                </div>
                                <div className="min-w-0 flex-1">
                                  <div
                                    className={`text-xs font-semibold truncate ${
                                      isCurrent ? "text-black font-bold" : "text-zinc-900"
                                    }`}
                                    title={doc.filename}
                                  >
                                    {cleanDocTitle(doc.filename)}
                                  </div>
                                  <div className="text-[10px] text-zinc-500 mt-1 flex flex-wrap items-center gap-x-2 gap-y-0.5">
                                    <span>{doc.page_count || doc.total_pages || 1} pages</span>
                                    <span>•</span>
                                    <span className="font-semibold capitalize text-black">
                                      {doc.status}
                                    </span>
                                  </div>
                                  <div className="text-[10px] text-zinc-400 mt-1 flex items-center gap-2">
                                    <span className="flex items-center gap-0.5" title="Uploaded date">
                                      <Calendar className="w-2.5 h-2.5" />
                                      {formatDate(doc.created_at)}
                                    </span>
                                    {doc.last_accessed_at && (
                                      <>
                                        <span>•</span>
                                        <span className="flex items-center gap-0.5" title="Last accessed">
                                          <Clock className="w-2.5 h-2.5" />
                                          {formatTime(doc.last_accessed_at)}
                                        </span>
                                      </>
                                    )}
                                  </div>
                                </div>
                              </div>

                              <div className="flex items-center gap-1 shrink-0">
                                {isCurrent && (
                                  <span className="px-1.5 py-0.5 bg-black text-white text-[9px] font-bold rounded-md">
                                    Active
                                  </span>
                                )}
                                <a
                                  href={api.getDocumentFileUrl(doc.document_id)}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  onClick={(e) => e.stopPropagation()}
                                  className="opacity-0 group-hover:opacity-100 p-1 text-zinc-400 hover:text-black hover:bg-zinc-100 rounded-lg transition-all cursor-pointer flex items-center justify-center"
                                  title="Open / Download saved PDF"
                                >
                                  <Download className="w-3.5 h-3.5" />
                                </a>
                                <button
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    setDocToDelete(doc);
                                  }}
                                  className="opacity-0 group-hover:opacity-100 p-1 text-zinc-400 hover:text-black hover:bg-zinc-100 rounded-lg transition-all cursor-pointer"
                                  title="Delete document"
                                >
                                  <Trash2 className="w-3.5 h-3.5" />
                                </button>
                              </div>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>
              )}

              {/* SECTION 2: RECENT CHATS */}
              {(activeView === "all" || activeView === "chats") && (
                <div>
                  <div className="text-[10px] font-bold text-zinc-400 uppercase tracking-wider px-1 mb-2 flex items-center justify-between">
                    <span className="flex items-center gap-1">
                      <MessageSquare className="w-3 h-3 text-zinc-400" />
                      RECENT CHATS ({conversations.length})
                    </span>
                    <button
                      onClick={onNewConversation}
                      className="text-black hover:text-zinc-600 transition-colors flex items-center gap-0.5 text-[10px] font-bold cursor-pointer"
                      title="Start a new chat (New Document)"
                    >
                      <Plus className="w-3 h-3" />
                      New Chat
                    </button>
                  </div>

                  {!activeDocument ? (
                    <div className="p-3 text-[11px] text-zinc-400 border border-dashed border-zinc-200 rounded-xl text-center bg-zinc-50">
                      Select a document to view chat history
                    </div>
                  ) : conversations.length === 0 ? (
                    <div className="p-4 text-xs text-zinc-500 border border-dashed border-zinc-200 rounded-xl text-center bg-zinc-50 space-y-2 animate-fade-in">
                      <div className="w-9 h-9 rounded-xl bg-zinc-100 text-zinc-400 flex items-center justify-center mx-auto">
                        <MessageSquare className="w-4 h-4" />
                      </div>
                      <div className="font-semibold text-zinc-700">No conversations yet</div>
                      <div className="text-[11px] text-zinc-400">
                        Ask your first question about this document.
                      </div>
                    </div>
                  ) : (
                    <div className="space-y-1">
                      {conversations.map((conv) => {
                        const isSelected = activeConversationId === conv.id;
                        return (
                          <div
                            key={conv.id}
                            onClick={() => onSelectConversation(conv.id)}
                            className={`group p-2 rounded-lg text-xs flex items-center justify-between gap-2 cursor-pointer transition-all duration-200 hover:translate-x-0.5 active:scale-[0.99] ${
                              isSelected
                                ? "bg-zinc-100 text-black font-semibold border border-zinc-300"
                                : "text-zinc-800 hover:bg-zinc-50 border border-transparent"
                            }`}
                          >
                            <div className="flex items-center gap-2 min-w-0 flex-1">
                              <MessageSquare
                                className={`w-3.5 h-3.5 shrink-0 ${
                                  isSelected ? "text-black" : "text-zinc-400"
                                }`}
                              />
                              <span className="truncate flex-1">{conv.title}</span>
                            </div>

                            <div className="flex items-center gap-0.5 shrink-0 opacity-0 group-hover:opacity-100 transition-opacity">
                              <button
                                onClick={(e) => handleAutoSummarize(e, conv)}
                                className="p-1 text-zinc-400 hover:text-black hover:bg-zinc-200 rounded transition-colors"
                                title="Summarize title from chat messages"
                              >
                                <Sparkles className="w-3 h-3 text-zinc-700" />
                              </button>
                              <button
                                onClick={(e) => handleStartRename(e, conv)}
                                className="p-1 text-zinc-400 hover:text-black hover:bg-zinc-200 rounded transition-colors"
                                title="Rename conversation"
                              >
                                <Edit2 className="w-3 h-3" />
                              </button>
                              <button
                                onClick={(e) => {
                                  e.stopPropagation();
                                  setConvToDelete(conv);
                                }}
                                className="p-1 text-zinc-400 hover:text-black hover:bg-zinc-200 rounded transition-colors"
                                title="Delete conversation"
                              >
                                <Trash2 className="w-3 h-3" />
                              </button>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* Bottom System & Engine Information */}
            <div className="pt-2 space-y-2 mt-2">
              <button
                onClick={() => setShowSettings(!showSettings)}
                className="w-full p-2 text-xs text-zinc-700 hover:bg-zinc-100 rounded-lg flex items-center justify-between transition-colors cursor-pointer"
              >
                <div className="flex items-center gap-2">
                  <Sliders className="w-3.5 h-3.5 text-zinc-500" />
                  <span>Architecture & Engine</span>
                </div>
                <span className="text-[10px] font-mono text-black font-bold">
                  Nemotron 3
                </span>
              </button>

              {showSettings && (
                <div className="bg-zinc-50 p-3 rounded-xl border border-zinc-200 space-y-2 text-xs animate-in fade-in duration-150">
                  <div>
                    <span className="text-[10px] font-semibold text-zinc-400 uppercase block">
                      Tutor LLM Model
                    </span>
                    <div className="flex items-center gap-1.5 font-medium text-black mt-0.5">
                      <Cpu className="w-3 h-3 text-black" />
                      <span>Nemotron 3 Nano (Ollama Cloud)</span>
                    </div>
                  </div>

                  <div>
                    <span className="text-[10px] font-semibold text-zinc-400 uppercase block">
                      Persistence & Vectors
                    </span>
                    <div className="flex items-center gap-1.5 font-medium text-black mt-0.5">
                      <Database className="w-3 h-3 text-black" />
                      <span>SQLite DB / Local Embeddings</span>
                    </div>
                  </div>

                  <div className="pt-1 border-t border-zinc-200 flex items-center gap-1 text-[10px] text-zinc-600">
                    <ShieldCheck className="w-3 h-3 text-black" />
                    <span>Backend-secured credentials</span>
                  </div>
                </div>
              )}

              {/* Status Pill */}
              <div className="flex items-center justify-between text-[11px] text-zinc-600 px-1 pt-1">
                <div className="flex items-center gap-1.5">
                  {isBackendOnline ? (
                    <CheckCircle2 className="w-3.5 h-3.5 text-black" />
                  ) : (
                    <XCircle className="w-3.5 h-3.5 text-zinc-400" />
                  )}
                  <span>
                    Backend:{" "}
                    <strong className="text-black">
                      {isBackendOnline ? "Online" : "Disconnected"}
                    </strong>
                  </span>
                </div>
                <div className="text-[10px] text-zinc-400 font-mono">
                  :8000
                </div>
              </div>
            </div>
          </div>
        ) : (
          /* Collapsed Icons Bar */
          <div className="hidden md:flex flex-1 flex-col items-center py-4 justify-between">
            <div className="space-y-4">
              {activeDocument && (
                <div
                  className="w-9 h-9 rounded-xl bg-zinc-100 text-black flex items-center justify-center border border-zinc-300"
                  title={`Active: ${activeDocument.filename}`}
                >
                  <FileText className="w-4 h-4" />
                </div>
              )}
            </div>

            <div
              className={`w-3 h-3 rounded-full ${
                isBackendOnline ? "bg-black" : "bg-zinc-300"
              }`}
              title={isBackendOnline ? "Backend Online" : "Backend Disconnected"}
            />
          </div>
        )}
      </aside>
    </>
  );
};
