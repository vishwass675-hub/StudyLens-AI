import React, { useState } from "react";
import { Check, Copy } from "lucide-react";

interface MarkdownContentProps {
  content: string;
}

export const MarkdownContent: React.FC<MarkdownContentProps> = ({ content }) => {
  // If no content, return empty
  if (!content) return null;

  // Split content into blocks: code blocks, tables, lists, headers, paragraphs
  const lines = content.split("\n");
  const blocks: React.ReactNode[] = [];

  let inCodeBlock = false;
  let codeBlockLanguage = "";
  let codeBlockLines: string[] = [];
  let blockKey = 0;

  let inTable = false;
  let tableLines: string[] = [];

  const flushCodeBlock = () => {
    if (codeBlockLines.length > 0 || inCodeBlock) {
      const codeText = codeBlockLines.join("\n");
      blocks.push(
        <CodeBlockView
          key={`code-${blockKey++}`}
          code={codeText}
          language={codeBlockLanguage}
        />
      );
      codeBlockLines = [];
      codeBlockLanguage = "";
      inCodeBlock = false;
    }
  };

  const flushTable = () => {
    if (tableLines.length > 0) {
      blocks.push(<TableView key={`table-${blockKey++}`} lines={tableLines} />);
      tableLines = [];
      inTable = false;
    }
  };

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];

    // Check code fence
    if (line.trim().startsWith("```")) {
      if (inCodeBlock) {
        flushCodeBlock();
      } else {
        if (inTable) flushTable();
        inCodeBlock = true;
        codeBlockLanguage = line.trim().slice(3).trim();
      }
      continue;
    }

    if (inCodeBlock) {
      codeBlockLines.push(line);
      continue;
    }

    // Check table line
    if (line.trim().startsWith("|") && line.trim().endsWith("|")) {
      inTable = true;
      tableLines.push(line);
      continue;
    } else if (inTable) {
      flushTable();
    }

    // Check headings
    if (line.startsWith("### ")) {
      blocks.push(
        <h3
          key={`h3-${blockKey++}`}
          className="text-sm font-bold text-slate-800 mt-4 mb-1.5 tracking-tight"
        >
          {renderInlineMarkdown(line.slice(4))}
        </h3>
      );
      continue;
    }
    if (line.startsWith("## ")) {
      blocks.push(
        <h2
          key={`h2-${blockKey++}`}
          className="text-base font-bold text-slate-900 mt-4 mb-2 tracking-tight border-b border-slate-100 pb-1"
        >
          {renderInlineMarkdown(line.slice(3))}
        </h2>
      );
      continue;
    }
    if (line.startsWith("# ")) {
      blocks.push(
        <h1
          key={`h1-${blockKey++}`}
          className="text-lg font-bold text-slate-900 mt-5 mb-2.5 tracking-tight"
        >
          {renderInlineMarkdown(line.slice(2))}
        </h1>
      );
      continue;
    }

    // Check bullet list item
    if (line.trim().startsWith("- ") || line.trim().startsWith("* ") || line.trim().startsWith("• ")) {
      const cleanLine = line.trim().replace(/^[-*•]\s+/, "");
      blocks.push(
        <div key={`li-${blockKey++}`} className="flex items-start gap-2 my-1 pl-2">
          <span className="text-black font-bold leading-relaxed shrink-0">•</span>
          <span className="text-black leading-relaxed text-sm">
            {renderInlineMarkdown(cleanLine)}
          </span>
        </div>
      );
      continue;
    }

    // Check numbered list item (e.g. "1. ")
    const numMatch = line.trim().match(/^(\d+)\.\s+(.*)$/);
    if (numMatch) {
      blocks.push(
        <div key={`num-${blockKey++}`} className="flex items-start gap-2 my-1 pl-2">
          <span className="text-zinc-500 font-mono text-xs font-semibold leading-relaxed shrink-0">
            {numMatch[1]}.
          </span>
          <span className="text-black leading-relaxed text-sm">
            {renderInlineMarkdown(numMatch[2])}
          </span>
        </div>
      );
      continue;
    }

    // Empty line
    if (!line.trim()) {
      blocks.push(<div key={`sp-${blockKey++}`} className="h-2" />);
      continue;
    }

    // Standard paragraph
    blocks.push(
      <p key={`p-${blockKey++}`} className="my-1.5 leading-relaxed text-black text-sm">
        {renderInlineMarkdown(line)}
      </p>
    );
  }

  if (inCodeBlock) flushCodeBlock();
  if (inTable) flushTable();

  return <div className="space-y-0.5">{blocks}</div>;
};

// Inline markdown renderer: handles **bold**, *italic*, `code`
function renderInlineMarkdown(text: string): React.ReactNode {
  // Regex to match `code` or **bold** or *italic*
  const parts: React.ReactNode[] = [];
  const regex = /(`[^`]+`|\*\*[^*]+\*\*|\*[^*]+\*)/g;
  let lastIndex = 0;
  let match;

  while ((match = regex.exec(text)) !== null) {
    if (match.index > lastIndex) {
      parts.push(text.substring(lastIndex, match.index));
    }

    const token = match[0];
    if (token.startsWith("`") && token.endsWith("`")) {
      parts.push(
        <code
          key={`code-${match.index}`}
          className="bg-zinc-100 text-black font-mono text-xs px-1.5 py-0.5 rounded border border-zinc-300"
        >
          {token.slice(1, -1)}
        </code>
      );
    } else if (token.startsWith("**") && token.endsWith("**")) {
      parts.push(
        <strong key={`bold-${match.index}`} className="font-semibold text-slate-900">
          {token.slice(2, -2)}
        </strong>
      );
    } else if (token.startsWith("*") && token.endsWith("*")) {
      parts.push(
        <em key={`em-${match.index}`} className="italic text-slate-800">
          {token.slice(1, -1)}
        </em>
      );
    }

    lastIndex = regex.lastIndex;
  }

  if (lastIndex < text.length) {
    parts.push(text.substring(lastIndex));
  }

  return parts.length > 0 ? parts : text;
}

// Code Block View component with copy button
const CodeBlockView: React.FC<{ code: string; language: string }> = ({ code, language }) => {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="my-3 rounded-xl overflow-hidden border border-slate-800 bg-slate-900 text-slate-100 shadow-sm">
      <div className="flex items-center justify-between px-3.5 py-1.5 bg-slate-950 border-b border-slate-800 text-[11px] text-slate-400">
        <span className="font-mono uppercase">{language || "text"}</span>
        <button
          onClick={handleCopy}
          className="flex items-center gap-1 hover:text-slate-200 transition-colors p-1 cursor-pointer"
        >
          {copied ? (
            <>
              <Check className="w-3 h-3 text-white" />
              <span className="text-white">Copied</span>
            </>
          ) : (
            <>
              <Copy className="w-3 h-3" />
              <span>Copy</span>
            </>
          )}
        </button>
      </div>
      <pre className="p-3.5 overflow-x-auto text-xs font-mono leading-relaxed">
        <code>{code}</code>
      </pre>
    </div>
  );
};

// Markdown Table View component
const TableView: React.FC<{ lines: string[] }> = ({ lines }) => {
  if (lines.length < 2) return null;

  const rows = lines
    .map((l) =>
      l
        .split("|")
        .slice(1, -1)
        .map((cell) => cell.trim())
    )
    .filter((r) => r.length > 0 && !r.every((c) => /^[-:]+$/.test(c)));

  if (rows.length === 0) return null;

  const [header, ...body] = rows;

  return (
    <div className="my-3 overflow-x-auto rounded-lg border border-slate-200 shadow-2xs">
      <table className="min-w-full divide-y divide-slate-200 text-xs text-left">
        <thead className="bg-slate-50 text-slate-700 font-semibold">
          <tr>
            {header.map((col, idx) => (
              <th key={idx} className="px-3 py-2 border-r last:border-r-0 border-slate-200">
                {col}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100 bg-white text-slate-800">
          {body.map((row, rIdx) => (
            <tr key={rIdx} className="hover:bg-slate-50/50">
              {row.map((cell, cIdx) => (
                <td key={cIdx} className="px-3 py-2 border-r last:border-r-0 border-slate-100">
                  {renderInlineMarkdown(cell)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};
