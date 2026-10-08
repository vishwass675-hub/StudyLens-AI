import React, { useState, useRef } from "react";
import { Upload, FileText, CheckCircle2, Loader2, X, AlertCircle } from "lucide-react";
import { DocumentMetadata } from "@/lib/types";

interface PDFUploaderProps {
  isOpen: boolean;
  onClose: () => void;
  onUpload: (file: File) => Promise<DocumentMetadata>;
  isProcessing: boolean;
}

export const PDFUploader: React.FC<PDFUploaderProps> = ({
  isOpen,
  onClose,
  onUpload,
  isProcessing,
}) => {
  const [dragActive, setDragActive] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [uploadSuccessDoc, setUploadSuccessDoc] = useState<DocumentMetadata | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  if (!isOpen) return null;

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const validateAndSetFile = (file: File) => {
    setError(null);
    setUploadSuccessDoc(null);
    if (!file.name.toLowerCase().endsWith(".pdf")) {
      setError("Please select a valid PDF file (.pdf).");
      return;
    }
    if (file.size > 50 * 1024 * 1024) {
      setError("PDF size exceeds the 50MB limit.");
      return;
    }
    setSelectedFile(file);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      validateAndSetFile(e.dataTransfer.files[0]);
    }
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    e.preventDefault();
    if (e.target.files && e.target.files[0]) {
      validateAndSetFile(e.target.files[0]);
    }
  };

  const handleSubmit = async () => {
    if (!selectedFile || isProcessing) return;
    try {
      setError(null);
      const doc = await onUpload(selectedFile);
      if (doc && doc.status === "ready") {
        setUploadSuccessDoc(doc);
        setTimeout(() => {
          onClose();
          setSelectedFile(null);
          setUploadSuccessDoc(null);
        }, 1200);
      } else {
        onClose();
        setSelectedFile(null);
      }
    } catch (err: unknown) {
      const msg =
        err instanceof Error
          ? err.message
          : "We couldn't process this document. Please try uploading it again.";
      setError(msg);
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/50 flex items-center justify-center p-4 animate-in fade-in duration-200 backdrop-blur-xs">
      <div className="bg-white rounded-2xl max-w-md w-full border border-zinc-200 shadow-2xl overflow-hidden animate-scale-up">
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-zinc-100">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-zinc-100 text-black border border-zinc-200 flex items-center justify-center animate-float">
              <Upload className="w-4 h-4" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-black">
                Upload Academic Document
              </h3>
              <p className="text-xs text-zinc-500">
                Supports research papers, textbooks, and lecture notes
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            disabled={isProcessing}
            className="text-zinc-400 hover:text-black p-1 rounded-lg transition-colors cursor-pointer"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Drop Area & Content */}
        <div className="p-5">
          <div
            onDragEnter={handleDrag}
            onDragLeave={handleDrag}
            onDragOver={handleDrag}
            onDrop={handleDrop}
            onClick={() => !isProcessing && fileInputRef.current?.click()}
            className={`border-2 border-dashed rounded-xl p-6 text-center cursor-pointer transition-all ${
              dragActive
                ? "border-black bg-zinc-50"
                : uploadSuccessDoc
                ? "border-zinc-400 bg-zinc-50"
                : selectedFile
                ? "border-black bg-zinc-50/50"
                : "border-zinc-300 hover:border-black bg-zinc-50/50"
            }`}
          >
            <input
              ref={fileInputRef}
              type="file"
              accept=".pdf,application/pdf"
              className="hidden"
              onChange={handleChange}
              disabled={isProcessing}
            />

            {uploadSuccessDoc ? (
              <div className="flex flex-col items-center animate-in zoom-in-95 duration-150">
                <div className="w-10 h-10 rounded-xl bg-zinc-100 text-black border border-zinc-300 flex items-center justify-center mb-2">
                  <CheckCircle2 className="w-5 h-5 text-black" />
                </div>
                <div className="text-xs font-semibold text-black max-w-xs truncate">
                  Ready to study
                </div>
                <div className="text-[11px] text-zinc-500 mt-0.5">
                  {uploadSuccessDoc.filename} ({uploadSuccessDoc.page_count} pages)
                </div>
              </div>
            ) : selectedFile ? (
              <div className="flex flex-col items-center">
                <div className="w-10 h-10 rounded-xl bg-zinc-100 text-black border border-zinc-300 flex items-center justify-center mb-2">
                  <FileText className="w-5 h-5" />
                </div>
                <div className="text-xs font-semibold text-black max-w-xs truncate">
                  {selectedFile.name}
                </div>
                <div className="text-[11px] text-zinc-500 mt-0.5">
                  {(selectedFile.size / (1024 * 1024)).toFixed(2)} MB • Ready to process
                </div>
              </div>
            ) : (
              <div className="flex flex-col items-center">
                <div className="w-10 h-10 rounded-xl bg-zinc-100 text-black border border-zinc-200 flex items-center justify-center mb-2">
                  <FileText className="w-5 h-5" />
                </div>
                <div className="text-xs font-semibold text-black">
                  Drop your PDF here, or{" "}
                  <span className="underline hover:text-zinc-600">browse</span>
                </div>
                <div className="text-[11px] text-zinc-500 mt-1">
                  PDF up to 50MB (academic papers, notes, thesis)
                </div>
              </div>
            )}
          </div>

          {error && (
            <div className="text-xs text-black bg-zinc-100 p-2.5 rounded-lg border border-zinc-300 mt-3 flex items-start gap-2">
              <AlertCircle className="w-4 h-4 shrink-0 mt-0.5 text-black" />
              <span>{error}</span>
            </div>
          )}

          {isProcessing && (
            <div className="mt-4 p-3 bg-zinc-50 rounded-xl border border-zinc-200 text-xs text-black space-y-2">
              <div className="flex items-center gap-2 font-semibold text-black">
                <Loader2 className="w-4 h-4 animate-spin text-black shrink-0" />
                <span>Processing document & preparing your AI tutor...</span>
              </div>
              <p className="text-[11px] text-zinc-600 pl-6 leading-relaxed">
                Extracting page-by-page text, generating vector embeddings, and indexing in vector store.
              </p>
            </div>
          )}

          {/* Action Buttons */}
          <div className="flex items-center justify-end gap-2 mt-5">
            <button
              onClick={onClose}
              disabled={isProcessing}
              className="px-3.5 py-2 text-xs font-medium text-zinc-600 hover:bg-zinc-100 rounded-xl transition-colors cursor-pointer disabled:cursor-not-allowed"
            >
              Cancel
            </button>
            <button
              onClick={handleSubmit}
              disabled={!selectedFile || isProcessing || !!uploadSuccessDoc}
              className="px-4 py-2 text-xs font-semibold bg-black hover:bg-zinc-800 disabled:bg-zinc-200 text-white disabled:text-zinc-400 rounded-xl transition-all duration-200 hover:scale-[1.02] active:scale-[0.98] cursor-pointer disabled:cursor-not-allowed flex items-center gap-1.5 shadow-xs"
            >
              {isProcessing && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
              {isProcessing ? "Processing..." : "Process Document"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
