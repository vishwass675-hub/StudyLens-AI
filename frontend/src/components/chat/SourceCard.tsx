import React from "react";
import { SourceReference } from "@/lib/types";
import { BookOpen, FileText } from "lucide-react";

interface SourceCardProps {
  source: SourceReference;
  index: number;
}

export const SourceCard: React.FC<SourceCardProps> = ({ source, index }) => {
  return (
    <div className="bg-white border border-zinc-200 rounded-lg p-2.5 text-xs text-black hover:border-black transition-all flex items-center justify-between gap-3 shadow-xs">
      <div className="flex items-center gap-2 min-w-0">
        <span className="flex items-center gap-1.5 bg-zinc-100 text-black px-2.5 py-1 rounded-md font-semibold border border-zinc-300 shrink-0">
          <BookOpen className="w-3.5 h-3.5 text-black" />
          Page {source.page}
        </span>
        {source.document && (
          <span className="text-zinc-600 truncate text-[11px] flex items-center gap-1">
            <FileText className="w-3 h-3 text-zinc-400 shrink-0" />
            <span className="truncate">{source.document}</span>
          </span>
        )}
      </div>

      <span className="text-[10px] text-zinc-400 font-mono shrink-0">
        Source #{index + 1}
      </span>
    </div>
  );
};
