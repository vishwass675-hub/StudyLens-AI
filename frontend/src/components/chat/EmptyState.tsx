import React from "react";
import { DocumentMetadata } from "@/lib/types";
import {
  Upload,
  FileText,
  CheckCircle2,
  HelpCircle,
  BookOpen,
  Sparkles,
  Award,
  GraduationCap,
  MessageSquare,
  Plus,
} from "lucide-react";

function cleanDocTitle(filename: string): string {
  return filename.replace(/^\d+[-_]/, "");
}

interface EmptyStateProps {
  document: DocumentMetadata | null;
  onOpenUpload: () => void;
  onSelectPrompt: (prompt: string) => void;
}

export const EmptyState: React.FC<EmptyStateProps> = ({
  document,
  onOpenUpload,
  onSelectPrompt,
}) => {
  const starterQuestions = [
    {
      icon: BookOpen,
      text: "What is this chapter about?",
      description: "Get a comprehensive high-level overview of the material.",
    },
    {
      icon: Sparkles,
      text: "Explain the most important concept.",
      description: "Unpack key theories, definitions, and core arguments.",
    },
    {
      icon: HelpCircle,
      text: "Give me a simple explanation of this topic.",
      description: "Break down complex academic concepts into intuitive terms.",
    },
    {
      icon: Award,
      text: "What should I study for my exam?",
      description: "Identify high-yield exam takeaways, formulas, and definitions.",
    },
  ];

  // 1. Initial Welcome State (Before PDF is uploaded)
  if (!document) {
    return (
      <div className="h-full w-full flex flex-col items-center justify-center p-4 md:p-6 max-w-md mx-auto text-center animate-fade-in overflow-hidden select-none">
        <div className="w-12 h-12 rounded-2xl bg-zinc-100 border border-zinc-200 flex items-center justify-center text-black mb-3 shadow-2xs animate-float">
          <GraduationCap className="w-6 h-6" />
        </div>

        <h1 className="text-2xl font-extrabold text-black tracking-tight">
          StudyLens AI
        </h1>
        <p className="text-xs md:text-sm text-zinc-600 font-medium mt-1 max-w-sm leading-relaxed">
          Upload your academic PDF to start learning with your grounded AI tutor.
        </p>
        <p className="text-[11px] text-zinc-400 mt-0.5 mb-5 max-w-xs">
          Strictly grounded citations, interactive summaries, revision notes, and quizzes.
        </p>

        {/* Dashboard Upload Card with Plus Sign */}
        <div
          onClick={onOpenUpload}
          className="group w-full max-w-sm bg-zinc-50 hover:bg-zinc-100 rounded-2xl p-6 shadow-xs text-center space-y-3 transition-all cursor-pointer hover:scale-[1.01]"
        >
          <div className="w-12 h-12 rounded-xl bg-black text-white flex items-center justify-center mx-auto shadow-xs group-hover:scale-105 transition-transform">
            <Plus className="w-6 h-6 stroke-[2.5]" />
          </div>

          <div className="space-y-0.5">
            <div className="text-sm font-bold text-black">
              Upload Academic PDF
            </div>
            <div className="text-xs text-zinc-500">
              Drag and drop your file here, or click to browse
            </div>
          </div>

          <div className="pt-1">
            <button
              onClick={(e) => {
                e.stopPropagation();
                onOpenUpload();
              }}
              className="px-5 py-2 bg-black hover:bg-zinc-800 text-white text-xs font-semibold rounded-xl inline-flex items-center gap-2 shadow-xs transition-all cursor-pointer hover:scale-[1.02]"
            >
              <Plus className="w-4 h-4 stroke-[2.5]" />
              <span>Upload File</span>
            </button>
          </div>

          <div className="text-[10px] text-zinc-400">
            Supports PDF files up to 50MB
          </div>
        </div>
      </div>
    );
  }

  // 2. Chat Empty State (PDF ready, awaiting first question)
  return (
    <div className="h-full w-full flex flex-col items-center justify-center p-4 md:p-6 max-w-2xl mx-auto w-full text-center animate-fade-in overflow-hidden">
      {/* Active Document Status Card */}
      <div className="bg-zinc-50 border border-zinc-200 rounded-2xl p-4 mb-5 w-full text-left flex flex-wrap items-center justify-between gap-3 shadow-xs hover-lift transition-all">
        <div className="flex items-center gap-3 min-w-0">
          <div className="w-10 h-10 rounded-xl bg-zinc-100 text-black border border-zinc-200 flex items-center justify-center shrink-0">
            <FileText className="w-5 h-5" />
          </div>
          <div className="min-w-0">
            <div className="text-xs font-semibold text-black truncate max-w-xs md:max-w-md">
              {cleanDocTitle(document.filename)}
            </div>
            <div className="text-[11px] text-zinc-500 mt-0.5 flex items-center gap-2">
              <span className="text-black font-medium flex items-center gap-1">
                <CheckCircle2 className="w-3 h-3 text-black" />
                Ready to study
              </span>
              <span>•</span>
              <span>{document.page_count || document.total_pages} pages</span>
            </div>
          </div>
        </div>

        <button
          onClick={onOpenUpload}
          className="flex items-center gap-1.5 px-3 py-1.5 bg-white hover:bg-zinc-100 text-black border border-zinc-300 rounded-lg text-xs font-semibold transition-all duration-200 hover:scale-[1.02] active:scale-[0.98] cursor-pointer shadow-2xs"
          title="Upload a new PDF document"
        >
          <Plus className="w-3.5 h-3.5 stroke-[2.5]" />
          <span>Upload File</span>
        </button>
      </div>

      {/* No conversations banner */}
      <div className="w-full text-left bg-zinc-50 border border-zinc-200 rounded-xl p-3.5 mb-6 flex items-center gap-3">
        <div className="w-8 h-8 rounded-lg bg-zinc-200 text-black flex items-center justify-center shrink-0">
          <MessageSquare className="w-4 h-4" />
        </div>
        <div>
          <div className="text-xs font-bold text-black">
            No conversations yet
          </div>
          <div className="text-[11px] text-zinc-500 mt-0.5">
            Ask your first question about this document or choose a starter below.
          </div>
        </div>
      </div>

      {/* Suggested Starter Questions */}
      <div className="w-full text-left">
        <div className="text-xs font-semibold text-zinc-400 uppercase tracking-wider mb-3">
          Suggested Questions:
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {starterQuestions.map((q, idx) => {
            const Icon = q.icon;
            return (
              <button
                key={idx}
                onClick={() => onSelectPrompt(q.text)}
                className="p-3.5 rounded-xl border border-zinc-200 bg-white hover:border-black hover:bg-zinc-50 transition-all duration-200 text-left group cursor-pointer hover-lift active:scale-[0.98] shadow-xs"
              >
                <div className="flex items-center gap-2 text-xs font-semibold text-black group-hover:text-black mb-1">
                  <Icon className="w-3.5 h-3.5 text-zinc-400 group-hover:text-black shrink-0 transition-colors" />
                  <span>&quot;{q.text}&quot;</span>
                </div>
                <div className="text-[11px] text-zinc-500 leading-normal pl-5.5">
                  {q.description}
                </div>
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
};
