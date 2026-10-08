import React, { useState, useEffect } from "react";
import { DocumentMetadata, SummaryResponse } from "@/lib/types";
import { api, ApiError } from "@/lib/api";
import {
  FileText,
  Sparkles,
  Copy,
  Check,
  RotateCcw,
  BookOpen,
  CheckCircle2,
  AlertTriangle,
  Tag,
  Loader2,
} from "lucide-react";

interface SummaryViewProps {
  document: DocumentMetadata | null;
}

function cleanDocTitle(filename: string): string {
  return filename.replace(/^\d+[-_]/, "");
}

export const SummaryView: React.FC<SummaryViewProps> = ({ document }) => {
  const [data, setData] = useState<SummaryResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  const fetchSummary = async (forceRegenerate = false) => {
    if (!document || document.status !== "ready") return;
    setIsLoading(true);
    setError(null);
    try {
      const res = await api.getSummary(document.document_id, forceRegenerate);
      setData(res);
    } catch (err: unknown) {
      const msg =
        err instanceof ApiError
          ? err.message
          : "We couldn't generate a summary for this document. Please try again.";
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
        const res = await api.getSummary(document.document_id, false);
        if (isMounted) setData(res);
      } catch (err: unknown) {
        if (isMounted) {
          const msg =
            err instanceof ApiError
              ? err.message
              : "We couldn't generate a summary for this document. Please try again.";
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
    const textToCopy = `DOCUMENT SUMMARY: ${document?.filename || "Academic Paper"}

OVERVIEW:
${data.document_overview}

MAIN TOPICS:
${data.topics.map((t) => `• ${t}`).join("\n")}

KEY TAKEAWAYS:
${data.key_takeaways.map((k) => `• ${k}`).join("\n")}

IMPORTANT DEFINITIONS:
${data.key_definitions.map((d) => `• ${d.term}: ${d.definition}`).join("\n")}

EXAM POINTS:
${data.exam_points.map((e) => `• ${e}`).join("\n")}
`;
    navigator.clipboard.writeText(textToCopy);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  if (!document || document.status !== "ready") {
    return (
      <div className="flex-1 flex flex-col items-center justify-center p-8 text-center max-w-md mx-auto animate-fade-in">
        <div className="w-12 h-12 rounded-2xl bg-zinc-100 text-zinc-500 border border-zinc-200 flex items-center justify-center mb-3">
          <FileText className="w-6 h-6" />
        </div>
        <h3 className="text-base font-bold text-black">
          Document Summary
        </h3>
        <p className="text-xs text-zinc-500 mt-1">
          Upload and index an academic PDF to automatically generate a grounded, comprehensive summary.
        </p>
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto p-4 md:p-8 max-w-4xl mx-auto w-full animate-fade-in">
      {/* Header bar */}
      <div className="flex flex-wrap items-center justify-between gap-3 pb-5 mb-6 border-b border-zinc-200">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-lg font-bold text-black tracking-tight flex items-center gap-2">
              <FileText className="w-5 h-5 text-black" />
              Document Summary
            </span>
            {data?.cached && (
              <span className="text-[10px] font-mono bg-zinc-100 text-zinc-600 px-2 py-0.5 rounded-full border border-zinc-200">
                Cached
              </span>
            )}
          </div>
          <p className="text-xs text-zinc-500 mt-0.5">
            Synthesized from {cleanDocTitle(document.filename)} ({document.page_count || document.total_pages} pages)
          </p>
        </div>

        <div className="flex items-center gap-2">
          {data && (
            <button
              onClick={handleCopy}
              className="px-3 py-1.5 text-xs font-medium text-black bg-white border border-zinc-300 hover:bg-zinc-50 rounded-lg transition-colors flex items-center gap-1.5 cursor-pointer shadow-xs"
            >
              {copied ? (
                <>
                  <Check className="w-3.5 h-3.5 text-black" />
                  <span className="text-black font-semibold">Copied</span>
                </>
              ) : (
                <>
                  <Copy className="w-3.5 h-3.5 text-zinc-500" />
                  <span>Copy Summary</span>
                </>
              )}
            </button>
          )}

          <button
            onClick={() => fetchSummary(true)}
            disabled={isLoading}
            className="px-3 py-1.5 text-xs font-medium text-black bg-zinc-100 border border-zinc-300 hover:bg-zinc-200 rounded-lg transition-colors flex items-center gap-1.5 cursor-pointer disabled:opacity-50"
            title="Regenerate summary"
          >
            <RotateCcw className={`w-3.5 h-3.5 ${isLoading ? "animate-spin" : ""}`} />
            <span>Regenerate</span>
          </button>
        </div>
      </div>

      {/* Loading State */}
      {isLoading && (
        <div className="space-y-4 py-8">
          <div className="flex items-center gap-2.5 text-xs font-semibold text-black bg-zinc-100 p-3 rounded-xl border border-zinc-300">
            <Loader2 className="w-4 h-4 animate-spin text-black" />
            <span>Synthesizing structured document summary with Nemotron 3 Nano...</span>
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
            <span>Failed to generate summary</span>
          </div>
          <p>{error}</p>
          <button
            onClick={() => fetchSummary(true)}
            className="px-3 py-1 bg-black text-white rounded-lg text-xs font-semibold hover:bg-zinc-800 cursor-pointer"
          >
            Try Again
          </button>
        </div>
      )}

      {/* Data presentation - Pure Monochrome */}
      {data && !isLoading && (
        <div className="space-y-6">
          {/* 1. Overview */}
          <div className="bg-white border border-zinc-200 rounded-2xl p-5 shadow-xs space-y-2">
            <h4 className="text-xs font-bold text-zinc-500 uppercase tracking-wider flex items-center gap-1.5">
              <FileText className="w-3.5 h-3.5 text-black" />
              Document Overview
            </h4>
            <p className="text-sm text-black leading-relaxed whitespace-pre-line">
              {data.document_overview}
            </p>
          </div>

          {/* 2. Main Topics */}
          {data.topics.length > 0 && (
            <div className="space-y-2">
              <h4 className="text-xs font-bold text-zinc-500 uppercase tracking-wider flex items-center gap-1.5">
                <Tag className="w-3.5 h-3.5 text-black" />
                Main Topics
              </h4>
              <div className="flex flex-wrap gap-2">
                {data.topics.map((t, idx) => (
                  <span
                    key={idx}
                    className="bg-zinc-100 text-black font-medium text-xs px-3 py-1.5 rounded-lg border border-zinc-200 flex items-center gap-1.5"
                  >
                    <span className="w-1.5 h-1.5 rounded-full bg-black" />
                    {t}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* 3. Key Takeaways */}
          {data.key_takeaways.length > 0 && (
            <div className="space-y-2">
              <h4 className="text-xs font-bold text-zinc-500 uppercase tracking-wider flex items-center gap-1.5">
                <CheckCircle2 className="w-3.5 h-3.5 text-black" />
                Key Takeaways
              </h4>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-2.5">
                {data.key_takeaways.map((point, idx) => (
                  <div
                    key={idx}
                    className="p-3.5 rounded-xl border border-zinc-200 bg-zinc-50/70 hover:bg-zinc-100 text-xs text-black leading-relaxed flex items-start gap-2.5 transition-colors"
                  >
                    <Check className="w-4 h-4 text-black shrink-0 mt-0.5" />
                    <span>{point}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* 4. Important Definitions */}
          {data.key_definitions.length > 0 && (
            <div className="space-y-2">
              <h4 className="text-xs font-bold text-zinc-500 uppercase tracking-wider flex items-center gap-1.5">
                <BookOpen className="w-3.5 h-3.5 text-black" />
                Important Definitions
              </h4>
              <div className="space-y-2">
                {data.key_definitions.map((def, idx) => (
                  <div
                    key={idx}
                    className="p-3.5 rounded-xl border border-zinc-200 bg-white text-xs space-y-1 shadow-2xs"
                  >
                    <div className="font-bold text-black text-xs">
                      {def.term}
                    </div>
                    <div className="text-zinc-600 leading-relaxed">
                      {def.definition}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* 5. Exam Points */}
          {data.exam_points.length > 0 && (
            <div className="bg-zinc-50 border border-zinc-300 rounded-2xl p-5 space-y-2">
              <h4 className="text-xs font-bold text-black uppercase tracking-wider flex items-center gap-1.5">
                <Sparkles className="w-3.5 h-3.5 text-black" />
                High-Yield Exam Focus
              </h4>
              <ul className="text-xs text-black space-y-1.5 pl-4 list-disc">
                {data.exam_points.map((ep, idx) => (
                  <li key={idx} className="leading-relaxed">
                    {ep}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* 6. Sources Attribution */}
          {data.sources.length > 0 && (
            <div className="pt-4 border-t border-zinc-200 text-xs text-zinc-500 flex flex-wrap items-center gap-2">
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
