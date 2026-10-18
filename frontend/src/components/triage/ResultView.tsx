import React, { useState } from 'react';
import { Copy, Check, Info } from 'lucide-react';
import { CitationCard } from './CitationCard';
import type { Citation, QueryResponse } from '../../types/triage';

interface ResultViewProps {
  question: string;
  response: QueryResponse;
  activeCitation?: Citation | null;
  onCitationClick: (citation: Citation) => void;
}

export const ResultView: React.FC<ResultViewProps> = ({
  question,
  response,
  activeCitation,
  onCitationClick,
}) => {
  const [copied, setCopied] = useState(false);

  const handleCopySummary = () => {
    const text = [
      `Query: ${question}`,
      `Answer:\n${response.answer}`,
      response.citations.length
        ? `Citations:\n${response.citations.map((c) => `[Page ${c.page}] ${c.quote}`).join('\n')}`
        : '',
    ]
      .filter(Boolean)
      .join('\n\n');

    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  return (
    <div className="p-4 space-y-4 text-xs font-sans">
      {/* Query Banner */}
      <div className="flex items-start justify-between pb-3 border-b border-[#1e232d] gap-2">
        <div>
          <span className="text-[10px] font-mono text-slate-500 uppercase">Query</span>
          <h3 className="text-xs font-medium text-slate-200 mt-0.5 selectable-text">
            {question}
          </h3>
        </div>

        <button
          onClick={handleCopySummary}
          className="h-6 px-2 text-[10px] font-mono text-slate-400 hover:text-slate-200 bg-[#161a22] hover:bg-[#1c212c] border border-[#1e232d] rounded flex items-center gap-1 transition-colors shrink-0"
        >
          {copied ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
          <span>{copied ? 'Copied' : 'Copy'}</span>
        </button>
      </div>

      {/* Answer Box: High-contrast, clean typography */}
      <div className="p-3.5 bg-[#161a22] rounded border border-[#1e232d]">
        <div className="flex items-center justify-between mb-2">
          <span className="text-[10px] font-mono text-slate-400 uppercase font-semibold">
            Synthesis
          </span>
          {!response.model_ready && (
            <span className="text-[10px] font-mono text-[#d4a359]">
              Fast Keyword Retrieval
            </span>
          )}
        </div>
        <p className="text-xs text-slate-100 font-sans leading-relaxed selectable-text">
          {response.answer}
        </p>
      </div>

      {/* Source Citations */}
      {response.citations && response.citations.length > 0 && (
        <div className="space-y-2">
          <span className="text-[10px] font-mono text-slate-500 uppercase block">
            Source Citations ({response.citations.length})
          </span>

          <div className="space-y-2">
            {response.citations.map((citation, idx) => {
              const isActive = Boolean(
                activeCitation &&
                activeCitation.page === citation.page &&
                activeCitation.quote === citation.quote
              );

              return (
                <CitationCard
                  key={idx}
                  citation={citation}
                  isActive={isActive}
                  onClick={() => onCitationClick(citation)}
                />
              );
            })}
          </div>
        </div>
      )}

      {/* Status Footer: Minimal disclaimer note at the bottom */}
      <div className="pt-3 border-t border-[#1e232d] flex items-start gap-1.5 text-[11px] text-slate-500">
        <Info className="w-3.5 h-3.5 shrink-0 mt-0.5 text-slate-600" />
        <span className="italic leading-relaxed">
          Automated clause verification. Always cross-examine against original contractual schedules.
        </span>
      </div>
    </div>
  );
};
