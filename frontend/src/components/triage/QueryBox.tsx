import React, { useState } from 'react';
import { Search, Loader2, ArrowRight } from 'lucide-react';

interface QueryBoxProps {
  value: string;
  onChange: (val: string) => void;
  onSubmit: (val: string) => void;
  isLoading: boolean;
  disabled?: boolean;
}

export const QueryBox: React.FC<QueryBoxProps> = ({
  value,
  onChange,
  onSubmit,
  isLoading,
  disabled = false,
}) => {
  const handleSubmit = (e?: React.FormEvent) => {
    e?.preventDefault();
    if (!value.trim() || isLoading || disabled) return;
    onSubmit(value.trim());
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      handleSubmit();
    }
  };

  return (
    <form
      onSubmit={handleSubmit}
      className="p-3 border-b border-[#1e232d] bg-[#11141a] flex items-center gap-2 shrink-0 z-20"
    >
      <div className="relative flex-1 flex items-center">
        <Search className="w-3.5 h-3.5 text-slate-500 absolute left-2.5 pointer-events-none" />
        <input
          type="text"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={disabled || isLoading}
          placeholder={
            disabled
              ? 'Load a document to run triage...'
              : 'Ask a legal or contractual question...'
          }
          className="w-full h-8 pl-8 pr-3 text-xs bg-[#0c0e12] text-slate-200 placeholder:text-slate-500 rounded border border-[#1e232d] focus:border-slate-500 focus:outline-none transition-colors"
        />
      </div>

      <button
        type="submit"
        disabled={disabled || isLoading || !value.trim()}
        className="h-8 px-3 text-xs font-semibold text-[#0c0e12] bg-[#d4a359] hover:bg-[#e6bc7a] disabled:opacity-40 disabled:pointer-events-none rounded flex items-center gap-1.5 transition-colors cursor-pointer shrink-0 shadow-sm"
      >
        {isLoading ? (
          <Loader2 className="w-3.5 h-3.5 animate-spin" />
        ) : (
          <>
            <span>Run Triage</span>
            <ArrowRight className="w-3 h-3" />
          </>
        )}
      </button>
    </form>
  );
};
