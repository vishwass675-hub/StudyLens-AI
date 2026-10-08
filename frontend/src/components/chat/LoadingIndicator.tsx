import React from "react";
import { Sparkles, GraduationCap } from "lucide-react";

export const LoadingIndicator: React.FC = () => {
  return (
    <div className="flex items-start gap-3.5 py-4 px-4 md:px-6 max-w-3xl mx-auto w-full animate-message-enter">
      <div className="w-8 h-8 rounded-xl bg-black flex items-center justify-center text-white shrink-0 border border-zinc-800 shadow-xs animate-float">
        <GraduationCap className="w-4 h-4" />
      </div>

      <div className="flex-1 space-y-3">
        <div className="flex items-center gap-2.5 text-xs font-medium text-black bg-zinc-100 px-3 py-1.5 rounded-full w-fit border border-zinc-200">
          <div className="flex items-center gap-1">
            <span className="w-1.5 h-1.5 rounded-full bg-black animate-wave-1" />
            <span className="w-1.5 h-1.5 rounded-full bg-black animate-wave-2" />
            <span className="w-1.5 h-1.5 rounded-full bg-black animate-wave-3" />
          </div>
          <span className="text-[11px] font-semibold text-zinc-800">StudyLens is thinking...</span>
        </div>

        <div className="space-y-2 pt-0.5 max-w-lg">
          <div className="h-3 rounded-full w-5/6 animate-shimmer" />
          <div className="h-3 rounded-full w-4/6 animate-shimmer" style={{ animationDelay: "0.2s" }} />
          <div className="h-3 rounded-full w-3/6 animate-shimmer" style={{ animationDelay: "0.4s" }} />
        </div>
      </div>
    </div>
  );
};
