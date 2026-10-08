import React, { useState } from "react";
import { ChatMessage } from "@/lib/types";
import { SourceCard } from "./SourceCard";
import { MarkdownContent } from "./MarkdownContent";
import {
  GraduationCap,
  User,
  ChevronDown,
  ChevronRight,
  BookOpen,
  Copy,
  Check,
  AlertCircle,
  Sparkles,
  HelpCircle,
  Award,
  Search,
} from "lucide-react";

interface MessageItemProps {
  message: ChatMessage;
  onQuickAction?: (actionType: "simpler" | "example" | "exam" | "quiz", lastContent: string) => void;
}

export const MessageItem: React.FC<MessageItemProps> = ({ message, onQuickAction }) => {
  const isUser = message.role === "user";
  const [sourcesOpen, setSourcesOpen] = useState(false);
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(message.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div
      className={`py-5 px-4 md:px-6 w-full animate-message-enter ${
        isUser
          ? "bg-transparent"
          : message.isError
          ? "bg-zinc-100 border-y border-zinc-300"
          : "bg-zinc-50/70 border-y border-zinc-200"
      }`}
    >
      <div className="max-w-3xl mx-auto flex items-start gap-3.5">
        {/* Avatar */}
        {isUser ? (
          <div className="w-8 h-8 rounded-xl bg-zinc-100 text-black flex items-center justify-center shrink-0 font-semibold text-xs border border-zinc-300">
            <User className="w-4 h-4" />
          </div>
        ) : message.isError ? (
          <div className="w-8 h-8 rounded-xl bg-zinc-200 text-black flex items-center justify-center shrink-0 border border-zinc-400">
            <AlertCircle className="w-4 h-4" />
          </div>
        ) : (
          <div className="w-8 h-8 rounded-xl bg-black text-white flex items-center justify-center shrink-0 border border-zinc-800 shadow-xs">
            <GraduationCap className="w-4 h-4" />
          </div>
        )}

        {/* Message Content */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between gap-2 mb-1.5">
            <span className="text-xs font-semibold text-black flex items-center gap-1.5">
              {isUser ? "You" : "StudyLens Tutor"}
              {message.timestamp && (
                <span className="text-[10px] text-zinc-400 font-normal">
                  {message.timestamp}
                </span>
              )}
            </span>
            {!isUser && (
              <button
                onClick={handleCopy}
                className="text-zinc-400 hover:text-black transition-colors p-1 rounded-md text-[11px] flex items-center gap-1 cursor-pointer"
                title="Copy answer"
              >
                {copied ? (
                  <>
                    <Check className="w-3.5 h-3.5 text-black" />
                    <span className="text-black font-semibold">Copied</span>
                  </>
                ) : (
                  <>
                    <Copy className="w-3.5 h-3.5 text-zinc-500" />
                    <span>Copy</span>
                  </>
                )}
              </button>
            )}
          </div>

          <div className="text-sm text-black leading-relaxed font-normal break-words">
            {isUser ? (
              <div className="whitespace-pre-wrap">{message.content}</div>
            ) : (
              <MarkdownContent content={message.content} />
            )}
          </div>

          {/* Quick Actions for Assistant Messages */}
          {!isUser && !message.isError && onQuickAction && (
            <div className="mt-3.5 pt-2.5 border-t border-zinc-200 flex flex-wrap items-center gap-1.5">
              <span className="text-[10px] font-semibold text-zinc-400 uppercase tracking-wider mr-1">
                Quick Actions:
              </span>
              <button
                type="button"
                onClick={() => onQuickAction("simpler", message.content)}
                className="px-2.5 py-1 bg-white hover:bg-zinc-100 border border-zinc-300 hover:border-black text-zinc-800 hover:text-black rounded-lg text-[11px] font-medium transition-all duration-200 hover:scale-[1.02] active:scale-[0.98] flex items-center gap-1 cursor-pointer shadow-xs"
                title="Re-explain in simpler language with everyday analogies"
              >
                <HelpCircle className="w-3 h-3 text-zinc-700" />
                <span>Explain Simpler</span>
              </button>

              <button
                type="button"
                onClick={() => onQuickAction("example", message.content)}
                className="px-2.5 py-1 bg-white hover:bg-zinc-100 border border-zinc-300 hover:border-black text-zinc-800 hover:text-black rounded-lg text-[11px] font-medium transition-all duration-200 hover:scale-[1.02] active:scale-[0.98] flex items-center gap-1 cursor-pointer shadow-xs"
                title="Provide an example grounded in the document"
              >
                <Search className="w-3 h-3 text-zinc-700" />
                <span>Give Example</span>
              </button>

              <button
                type="button"
                onClick={() => onQuickAction("exam", message.content)}
                className="px-2.5 py-1 bg-white hover:bg-zinc-100 border border-zinc-300 hover:border-black text-zinc-800 hover:text-black rounded-lg text-[11px] font-medium transition-all duration-200 hover:scale-[1.02] active:scale-[0.98] flex items-center gap-1 cursor-pointer shadow-xs"
                title="Convert into concise exam-oriented answer"
              >
                <Award className="w-3 h-3 text-zinc-700" />
                <span>Exam Answer</span>
              </button>

              <button
                type="button"
                onClick={() => onQuickAction("quiz", message.content)}
                className="px-2.5 py-1 bg-white hover:bg-zinc-100 border border-zinc-300 hover:border-black text-zinc-800 hover:text-black rounded-lg text-[11px] font-medium transition-all duration-200 hover:scale-[1.02] active:scale-[0.98] flex items-center gap-1 cursor-pointer shadow-xs"
                title="Generate a quiz on this topic"
              >
                <Sparkles className="w-3 h-3 text-zinc-700" />
                <span>Quiz Me</span>
              </button>
            </div>
          )}

          {/* Source References Section */}
          {!isUser && message.sources && message.sources.length > 0 && (
            <div className="mt-3.5 pt-2.5 border-t border-zinc-200">
              <div className="flex items-center justify-between">
                <button
                  onClick={() => setSourcesOpen(!sourcesOpen)}
                  className="flex items-center gap-1.5 text-xs font-semibold text-black hover:bg-zinc-200 bg-zinc-100 border border-zinc-300 px-2.5 py-1.5 rounded-lg transition-colors cursor-pointer"
                >
                  <BookOpen className="w-3.5 h-3.5 text-black" />
                  <span>Sources ({message.sources.length})</span>
                  {sourcesOpen ? (
                    <ChevronDown className="w-3.5 h-3.5 ml-1" />
                  ) : (
                    <ChevronRight className="w-3.5 h-3.5 ml-1" />
                  )}
                </button>
              </div>

              {sourcesOpen && (
                <div className="mt-2.5 space-y-1.5 animate-in fade-in duration-200">
                  <div className="text-[11px] text-zinc-500 font-medium mb-1">
                    Grounded citations retrieved from PDF:
                  </div>
                  {message.sources.map((src, idx) => (
                    <SourceCard key={`${src.document}-${src.page}-${idx}`} source={src} index={idx} />
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
