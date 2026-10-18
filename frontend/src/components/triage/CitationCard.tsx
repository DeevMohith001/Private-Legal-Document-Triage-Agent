import React, { useState } from 'react';
import { Copy, Check, ArrowUpRight } from 'lucide-react';
import type { Citation } from '../../types/triage';

interface CitationCardProps {
  citation: Citation;
  isActive?: boolean;
  onClick: () => void;
}

export const CitationCard: React.FC<CitationCardProps> = ({
  citation,
  isActive = false,
  onClick,
}) => {
  const [copied, setCopied] = useState(false);

  const handleCopy = (e: React.MouseEvent) => {
    e.stopPropagation();
    navigator.clipboard.writeText(citation.quote);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  return (
    <div
      onClick={onClick}
      className={`p-3 rounded border transition-colors cursor-pointer text-left select-none ${
        isActive
          ? 'border-[#d4a359] bg-[#161a22]'
          : 'border-[#1e232d] bg-[#11141a] hover:border-slate-500 hover:bg-[#161a22]'
      }`}
    >
      <div className="flex items-center justify-between mb-1.5">
        <span className="text-[10px] font-mono font-medium text-[#d4a359] px-1.5 py-0.5 rounded bg-[#d4a359]/10 border border-[#d4a359]/30">
          Page {citation.page}
        </span>

        <div className="flex items-center gap-2">
          <button
            onClick={handleCopy}
            className="p-1 rounded text-slate-500 hover:text-slate-300 transition-colors"
            title="Copy quote"
          >
            {copied ? (
              <Check className="w-3 h-3 text-emerald-400" />
            ) : (
              <Copy className="w-3 h-3" />
            )}
          </button>
          <span className="flex items-center gap-0.5 text-[10px] font-mono text-slate-400 hover:text-slate-200">
            <span>Jump</span>
            <ArrowUpRight className="w-3 h-3 text-slate-500" />
          </span>
        </div>
      </div>

      <p className="text-xs text-slate-200 font-sans italic leading-relaxed pl-2.5 border-l border-[#1e232d] selectable-text">
        "{citation.quote}"
      </p>
    </div>
  );
};
