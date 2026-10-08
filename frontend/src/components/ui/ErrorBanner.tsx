import React from "react";
import { AlertCircle, X, RefreshCw } from "lucide-react";

interface ErrorBannerProps {
  message: string;
  onDismiss?: () => void;
  onRetry?: () => void;
}

export const ErrorBanner: React.FC<ErrorBannerProps> = ({
  message,
  onDismiss,
  onRetry,
}) => {
  if (!message) return null;

  return (
    <div className="bg-zinc-100 border border-zinc-300 text-black px-4 py-3 rounded-xl flex items-start justify-between shadow-xs my-3 animate-in fade-in duration-200">
      <div className="flex items-start gap-3">
        <AlertCircle className="w-5 h-5 text-black mt-0.5 shrink-0" />
        <div>
          <div className="font-semibold text-sm text-black">Action Required</div>
          <div className="text-xs text-zinc-600 mt-0.5">{message}</div>
        </div>
      </div>
      <div className="flex items-center gap-2">
        {onRetry && (
          <button
            onClick={onRetry}
            className="text-xs font-semibold px-2.5 py-1 bg-black text-white hover:bg-zinc-800 rounded-lg flex items-center gap-1 transition-colors cursor-pointer"
          >
            <RefreshCw className="w-3 h-3" />
            Retry
          </button>
        )}
        {onDismiss && (
          <button
            onClick={onDismiss}
            className="text-zinc-400 hover:text-black p-1 rounded-lg transition-colors cursor-pointer"
            title="Dismiss"
          >
            <X className="w-4 h-4" />
          </button>
        )}
      </div>
    </div>
  );
};
