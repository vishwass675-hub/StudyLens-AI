import React, { useState, useRef, useEffect } from "react";
import { DocumentMetadata, TutorMode } from "@/lib/types";
import { ArrowUp, CornerDownLeft, Trash2, Sparkles } from "lucide-react";

function cleanDocTitle(filename: string): string {
  return filename.replace(/^\d+[-_]/, "");
}

interface ChatComposerProps {
  document: DocumentMetadata | null;
  isLoading: boolean;
  tutorMode: TutorMode;
  onChangeTutorMode: (mode: TutorMode) => void;
  onSendMessage: (message: string) => void;
  onClearChat?: () => void;
  hasMessages?: boolean;
}

export const ChatComposer: React.FC<ChatComposerProps> = ({
  document,
  isLoading,
  tutorMode,
  onChangeTutorMode,
  onSendMessage,
  onClearChat,
  hasMessages,
}) => {
  const [input, setInput] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const modes: { id: TutorMode; label: string; tooltip: string }[] = [
    { id: "simple", label: "Simple", tooltip: "Beginner-friendly explanation" },
    { id: "detailed", label: "Detailed", tooltip: "In-depth academic breakdown" },
    { id: "exam", label: "Exam", tooltip: "Exam preparation key points" },
    { id: "eli5", label: "ELI5", tooltip: "Explain like I'm 5 with analogies" },
  ];

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.height = `${Math.min(
        textareaRef.current.scrollHeight,
        180
      )}px`;
    }
  }, [input]);

  const handleSubmit = (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!input.trim() || isLoading || !document || document.status !== "ready") return;
    onSendMessage(input.trim());
    setInput("");
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const isReady = document && document.status === "ready";

  return (
    <div className="p-4 md:p-6 bg-white border-t border-zinc-100 sticky bottom-0 z-10">
      <div className="max-w-3xl mx-auto">
        {/* Tutor Mode Selector Bar & Clear Action */}
        <div className="flex flex-wrap items-center justify-between gap-2 text-xs mb-2 px-1">
          {/* Mode segmented control */}
          <div className="flex items-center gap-1 bg-zinc-100 p-0.5 rounded-lg border border-zinc-200">
            <span className="text-[10px] font-semibold text-zinc-500 uppercase px-2 py-1 flex items-center gap-1">
              <Sparkles className="w-2.5 h-2.5 text-black" /> Mode:
            </span>
            {modes.map((m) => (
              <button
                key={m.id}
                type="button"
                onClick={() => onChangeTutorMode(m.id)}
                title={m.tooltip}
                className={`px-2.5 py-1 rounded-md text-xs font-medium transition-all duration-200 cursor-pointer ${
                  tutorMode === m.id
                    ? "bg-black text-white shadow-xs font-semibold scale-100"
                    : "text-zinc-600 hover:text-black hover:bg-zinc-200/60"
                }`}
              >
                {m.label}
              </button>
            ))}
          </div>

          {/* Clear chat action */}
          {hasMessages && onClearChat && (
            <button
              onClick={onClearChat}
              className="text-zinc-400 hover:text-black transition-colors flex items-center gap-1 text-[11px] cursor-pointer"
              title="Clear chat messages"
            >
              <Trash2 className="w-3 h-3" />
              Clear chat
            </button>
          )}
        </div>

        {/* Input Box Card - Pure Monochrome */}
        <div className="relative bg-white border border-zinc-300 focus-within:border-black focus-within:ring-1 focus-within:ring-black rounded-2xl shadow-xs focus-within:shadow-md transition-all duration-200 overflow-hidden">
          <textarea
            ref={textareaRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={!isReady || isLoading}
            placeholder={
              !document
                ? "Upload a PDF above to begin asking questions..."
                : !isReady
                ? "Indexing document in vector store..."
                : `Ask your tutor in ${tutorMode.toUpperCase()} mode (e.g. concepts, formulas, definitions)...`
            }
            rows={1}
            className="w-full pl-4 pr-12 pt-3.5 pb-3 text-sm text-black placeholder:text-zinc-400 resize-none outline-none disabled:bg-zinc-50 disabled:cursor-not-allowed max-h-44 min-h-[50px] transition-colors"
          />

          <button
            onClick={() => handleSubmit()}
            disabled={!input.trim() || isLoading || !isReady}
            className={`absolute right-2.5 bottom-2.5 w-8 h-8 rounded-xl flex items-center justify-center transition-all duration-200 shadow-xs ${
              input.trim() && !isLoading && isReady
                ? "bg-black hover:bg-zinc-800 text-white cursor-pointer hover:scale-105 active:scale-95"
                : "bg-zinc-200 text-zinc-400 cursor-not-allowed scale-95"
            }`}
            title="Send question (Enter)"
          >
            <ArrowUp className="w-4 h-4 stroke-[2.5]" />
          </button>
        </div>

        {/* Footnote */}
        <div className="flex items-center justify-between text-[10px] text-zinc-400 mt-2 px-1">
          <span>
            {isReady
              ? `Connected to ${cleanDocTitle(document.filename)} • Grounded tutor responses`
              : "Upload an academic PDF to activate the grounded tutor"}
          </span>
          <span className="hidden sm:inline-flex items-center gap-1 font-mono">
            Enter <CornerDownLeft className="w-2.5 h-2.5" /> to send
          </span>
        </div>
      </div>
    </div>
  );
};
