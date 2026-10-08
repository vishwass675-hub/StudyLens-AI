import React, { useState, useEffect } from "react";
import { DocumentMetadata, NotesResponse } from "@/lib/types";
import { api, ApiError } from "@/lib/api";
import { MarkdownContent } from "@/components/chat/MarkdownContent";
import {
  Copy,
  Check,
  Download,
  RotateCcw,
  AlertTriangle,
  Loader2,
  Bookmark,
} from "lucide-react";

interface NotesViewProps {
  document: DocumentMetadata | null;
}

function cleanDocTitle(filename: string): string {
  return filename.replace(/^\d+[-_]/, "");
}

export const NotesView: React.FC<NotesViewProps> = ({ document }) => {
  const [data, setData] = useState<NotesResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  const fetchNotes = async (forceRegenerate = false) => {
    if (!document || document.status !== "ready") return;
    setIsLoading(true);
    setError(null);
    try {
      const res = await api.getNotes(document.document_id, forceRegenerate);
      setData(res);
    } catch (err: unknown) {
      const msg =
        err instanceof ApiError
          ? err.message
          : "We couldn't generate revision notes for this document. Please try again.";
      setError(msg);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    let isMounted = true;
    if (!document || document.status !== "ready") {
      return;
    }

    const load = async () => {
      setIsLoading(true);
      setError(null);
      try {
        const res = await api.getNotes(document.document_id, false);
        if (isMounted) setData(res);
      } catch (err: unknown) {
        if (isMounted) {
          const msg =
            err instanceof ApiError
              ? err.message
              : "We couldn't generate revision notes for this document. Please try again.";
          setError(msg);
        }
      } finally {
        if (isMounted) setIsLoading(false);
      }
    };

    load();
    return () => {
      isMounted = false;
    };
  }, [document?.document_id, document?.status]);

  const handleCopy = () => {
    if (!data) return;
    navigator.clipboard.writeText(data.markdown_content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleDownload = () => {
    if (!data) return;
    const blob = new Blob([data.markdown_content], { type: "text/markdown;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = window.document.createElement("a");
    a.href = url;
    a.download = `${document?.filename.replace(/\.pdf$/i, "") || "document"}_Revision_Notes.md`;
    window.document.body.appendChild(a);
    a.click();
    window.document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  if (!document || document.status !== "ready") {
    return (
      <div className="flex-1 flex flex-col items-center justify-center p-8 text-center max-w-md mx-auto animate-fade-in">
        <div className="w-12 h-12 rounded-2xl bg-zinc-100 text-zinc-500 border border-zinc-200 flex items-center justify-center mb-3">
          <Bookmark className="w-6 h-6" />
        </div>
        <h3 className="text-base font-bold text-black">
          Revision Notes
        </h3>
        <p className="text-xs text-zinc-500 mt-1">
          Upload and index an academic PDF to generate structured study notes with key definitions and exam tips.
        </p>
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto p-4 md:p-8 max-w-4xl mx-auto w-full animate-fade-in">
      {/* Header Bar */}
      <div className="flex flex-wrap items-center justify-between gap-3 pb-5 mb-6 border-b border-zinc-200">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-lg font-bold text-black tracking-tight flex items-center gap-2">
              <Bookmark className="w-5 h-5 text-black" />
              Revision Study Notes
            </span>
            {data?.cached && (
              <span className="text-[10px] font-mono bg-zinc-100 text-zinc-600 px-2 py-0.5 rounded-full border border-zinc-200">
                Cached
              </span>
            )}
          </div>
          <p className="text-xs text-zinc-500 mt-0.5">
            Grounded notes for {cleanDocTitle(document.filename)} ({document.page_count || document.total_pages} pages)
          </p>
        </div>

        <div className="flex items-center gap-2">
          {data && (
            <>
              <button
                onClick={handleCopy}
                className="px-3 py-1.5 text-xs font-medium text-black bg-white border border-zinc-300 hover:bg-zinc-50 rounded-lg transition-colors flex items-center gap-1.5 cursor-pointer shadow-xs"
                title="Copy markdown content"
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

              <button
                onClick={handleDownload}
                className="px-3 py-1.5 text-xs font-medium text-black bg-white border border-zinc-300 hover:bg-zinc-50 rounded-lg transition-colors flex items-center gap-1.5 cursor-pointer shadow-xs"
                title="Download markdown (.md)"
              >
                <Download className="w-3.5 h-3.5 text-zinc-500" />
                <span>Download .md</span>
              </button>
            </>
          )}

          <button
            onClick={() => fetchNotes(true)}
            disabled={isLoading}
            className="px-3 py-1.5 text-xs font-medium text-black bg-zinc-100 border border-zinc-300 hover:bg-zinc-200 rounded-lg transition-colors flex items-center gap-1.5 cursor-pointer disabled:opacity-50"
            title="Regenerate notes"
          >
            <RotateCcw className={`w-3.5 h-3.5 ${isLoading ? "animate-spin" : ""}`} />
            <span>Regenerate</span>
          </button>
        </div>
      </div>

      {/* Loading state */}
      {isLoading && (
        <div className="space-y-4 py-8">
          <div className="flex items-center gap-2.5 text-xs font-semibold text-black bg-zinc-100 p-3 rounded-xl border border-zinc-300">
            <Loader2 className="w-4 h-4 animate-spin text-black" />
            <span>Synthesizing structured revision notes with formulas & exam tips...</span>
          </div>
          <div className="space-y-3">
            <div className="h-4 bg-zinc-200 rounded-md w-full animate-pulse" />
            <div className="h-4 bg-zinc-200 rounded-md w-5/6 animate-pulse" />
            <div className="h-4 bg-zinc-200 rounded-md w-4/6 animate-pulse" />
          </div>
        </div>
      )}

      {/* Error state */}
      {error && !isLoading && (
        <div className="p-4 bg-zinc-100 border border-zinc-300 rounded-xl text-xs text-black space-y-2 mb-6">
          <div className="font-semibold flex items-center gap-1.5">
            <AlertTriangle className="w-4 h-4 text-black" />
            <span>Failed to generate revision notes</span>
          </div>
          <p>{error}</p>
          <button
            onClick={() => fetchNotes(true)}
            className="px-3 py-1 bg-black text-white rounded-lg text-xs font-semibold hover:bg-zinc-800 cursor-pointer"
          >
            Try Again
          </button>
        </div>
      )}

      {/* Notes Content */}
      {data && !isLoading && (
        <div className="bg-white border border-zinc-200 rounded-2xl p-6 md:p-8 shadow-xs space-y-6">
          <div className="prose prose-zinc max-w-none text-black">
            <MarkdownContent content={data.markdown_content} />
          </div>

          {/* Sources Footnote */}
          {data.sources.length > 0 && (
            <div className="pt-6 border-t border-zinc-200 text-xs text-zinc-500 flex flex-wrap items-center gap-2">
              <span className="font-semibold text-black">Grounded from:</span>
              {data.sources.map((s, idx) => (
                <span
                  key={idx}
                  className="bg-zinc-100 text-black px-2 py-0.5 rounded text-[11px] font-medium border border-zinc-300"
                >
                  Page {s.page}
                </span>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
};
