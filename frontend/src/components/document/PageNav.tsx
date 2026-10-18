import React, { useState, useEffect } from 'react';
import {
  ChevronLeft,
  ChevronRight,
  ZoomIn,
  ZoomOut,
  Maximize2,
  FolderOpen,
} from 'lucide-react';

interface PageNavProps {
  filename: string;
  currentPage: number;
  totalPages: number;
  zoom: number;
  isCurrentPageOcr?: boolean;
  onPageChange: (page: number) => void;
  onZoomChange: (zoom: number) => void;
  onFitWidth: () => void;
  onResetZoom: () => void;
  onNewUpload?: () => void;
}

export const PageNav: React.FC<PageNavProps> = ({
  filename,
  currentPage,
  totalPages,
  zoom,
  isCurrentPageOcr = false,
  onPageChange,
  onZoomChange,
  onFitWidth,
  onResetZoom,
  onNewUpload,
}) => {
  const [pageInput, setPageInput] = useState<string>(String(currentPage));

  useEffect(() => {
    setPageInput(String(currentPage));
  }, [currentPage]);

  const handlePageInputSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const parsed = parseInt(pageInput, 10);
    if (!isNaN(parsed) && parsed >= 1 && parsed <= totalPages) {
      onPageChange(parsed);
    } else {
      setPageInput(String(currentPage));
    }
  };

  return (
    <div className="h-8 border-b border-[#1e232d] bg-[#11141a] px-3 flex items-center justify-between text-xs select-none shrink-0 z-20">
      {/* Left: Filename */}
      <div className="flex items-center gap-2 max-w-[35%]">
        <span className="text-[11px] font-mono text-slate-300 truncate" title={filename}>
          {filename}
        </span>
      </div>

      {/* Middle: Page Counter (Page X of Y) */}
      <div className="flex items-center gap-1 bg-[#161a22] px-1.5 py-0.5 rounded border border-[#1e232d]">
        <button
          disabled={currentPage <= 1}
          onClick={() => onPageChange(currentPage - 1)}
          className="p-0.5 rounded text-slate-400 hover:text-slate-100 disabled:opacity-30 disabled:pointer-events-none"
          title="Previous page"
        >
          <ChevronLeft className="w-3 h-3" />
        </button>

        <form onSubmit={handlePageInputSubmit} className="flex items-center gap-1">
          <input
            type="text"
            value={pageInput}
            onChange={(e) => setPageInput(e.target.value)}
            onBlur={handlePageInputSubmit}
            className="w-7 h-4 text-center font-mono text-[11px] bg-[#0c0e12] text-slate-200 rounded border border-[#1e232d] focus:outline-none"
          />
          <span className="text-slate-500 font-mono text-[11px]">of {totalPages || 1}</span>
        </form>

        <button
          disabled={currentPage >= totalPages}
          onClick={() => onPageChange(currentPage + 1)}
          className="p-0.5 rounded text-slate-400 hover:text-slate-100 disabled:opacity-30 disabled:pointer-events-none"
          title="Next page"
        >
          <ChevronRight className="w-3 h-3" />
        </button>
      </div>

      {/* Right: OCR Indicator & Zoom Controls */}
      <div className="flex items-center gap-2">
        {/* OCR indicator tag */}
        <span
          className={`text-[10px] font-mono px-1.5 py-0.5 rounded border ${
            isCurrentPageOcr
              ? 'bg-[#d4a359]/10 text-[#e6bc7a] border-[#d4a359]/30'
              : 'bg-[#161a22] text-slate-400 border-[#1e232d]'
          }`}
        >
          {isCurrentPageOcr ? 'RapidOCR Page' : 'Native Text'}
        </span>

        {/* Zoom Controls */}
        <div className="flex items-center gap-0.5 pl-1.5 border-l border-[#1e232d]">
          <button
            disabled={zoom <= 0.5}
            onClick={() => onZoomChange(Math.max(0.5, zoom - 0.15))}
            className="p-1 rounded text-slate-400 hover:text-slate-200 disabled:opacity-30"
            title="Zoom out"
          >
            <ZoomOut className="w-3 h-3" />
          </button>

          <button
            onClick={onResetZoom}
            className="px-1 text-[11px] font-mono text-slate-400 hover:text-slate-200"
            title="Reset zoom"
          >
            {Math.round(zoom * 100)}%
          </button>

          <button
            disabled={zoom >= 2.5}
            onClick={() => onZoomChange(Math.min(2.5, zoom + 0.15))}
            className="p-1 rounded text-slate-400 hover:text-slate-200 disabled:opacity-30"
            title="Zoom in"
          >
            <ZoomIn className="w-3 h-3" />
          </button>

          <button
            onClick={onFitWidth}
            className="p-1 rounded text-slate-400 hover:text-slate-200"
            title="Fit width"
          >
            <Maximize2 className="w-3 h-3" />
          </button>
        </div>

        {onNewUpload && (
          <button
            onClick={onNewUpload}
            className="p-1 rounded text-slate-400 hover:text-slate-100 hover:bg-[#161a22]"
            title="Open another document"
          >
            <FolderOpen className="w-3 h-3" />
          </button>
        )}
      </div>
    </div>
  );
};
