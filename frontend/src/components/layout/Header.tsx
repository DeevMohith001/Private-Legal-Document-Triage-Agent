import React from 'react';
import { Upload } from 'lucide-react';

interface HeaderProps {
  documentName?: string;
  totalPages?: number;
  latencyMs?: number | null;
  isBackendOnline?: boolean;
  onOpenDocument: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  documentName,
  totalPages,
  latencyMs,
  isBackendOnline = true,
  onOpenDocument,
}) => {
  return (
    <header className="h-10 border-b border-[#1e232d] bg-[#11141a] px-3.5 flex items-center justify-between select-none shrink-0 z-30">
      {/* Left: Branding & Active Document */}
      <div className="flex items-center gap-3">
        <span className="text-[13px] font-semibold tracking-tight text-slate-100 font-sans">
          LexisEdge
        </span>

        {documentName && (
          <div className="flex items-center gap-1.5 pl-3 border-l border-[#1e232d]">
            <span className="text-[11px] font-mono text-slate-300 max-w-[320px] truncate">
              {documentName}
            </span>
          </div>
        )}
      </div>

      {/* Right: Operational indicators & Load Document button */}
      <div className="flex items-center gap-3">
        {/* Page Count */}
        {totalPages !== undefined && totalPages > 0 && (
          <div className="text-[11px] font-mono text-slate-400">
            {totalPages} {totalPages === 1 ? 'Page' : 'Pages'}
          </div>
        )}

        {/* Backend Latency / Ping */}
        <div className="flex items-center gap-1.5 text-[11px] font-mono text-slate-400">
          <span
            className={`w-1.5 h-1.5 rounded-full ${
              isBackendOnline ? 'bg-emerald-500' : 'bg-rose-500'
            }`}
          />
          <span>
            {isBackendOnline
              ? latencyMs !== null && latencyMs !== undefined
                ? `${latencyMs}ms`
                : 'Connected'
              : 'Offline'}
          </span>
        </div>

        {/* Load Document Button */}
        <button
          onClick={onOpenDocument}
          className="h-6 px-2.5 text-xs font-medium text-slate-200 bg-[#161a22] hover:bg-[#1c212c] border border-[#1e232d] hover:border-slate-600 rounded flex items-center gap-1.5 transition-colors cursor-pointer"
        >
          <Upload className="w-3 h-3 text-slate-400" />
          <span>Load Document</span>
        </button>
      </div>
    </header>
  );
};
