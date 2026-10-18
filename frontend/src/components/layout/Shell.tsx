import React, { useState, useRef, useCallback, useEffect } from 'react';

interface ShellProps {
  leftPanel: React.ReactNode;
  rightPanel: React.ReactNode;
  defaultLeftPercent?: number;
}

export const Shell: React.FC<ShellProps> = ({
  leftPanel,
  rightPanel,
  defaultLeftPercent = 58,
}) => {
  const [leftPercent, setLeftPercent] = useState<number>(defaultLeftPercent);
  const [isDragging, setIsDragging] = useState<boolean>(false);
  const containerRef = useRef<HTMLDivElement>(null);

  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleMouseMove = useCallback(
    (e: MouseEvent) => {
      if (!isDragging || !containerRef.current) return;
      const rect = containerRef.current.getBoundingClientRect();
      const currentX = e.clientX - rect.left;
      const newPercent = (currentX / rect.width) * 100;
      setLeftPercent(Math.max(25, Math.min(80, newPercent)));
    },
    [isDragging]
  );

  const handleMouseUp = useCallback(() => {
    if (isDragging) {
      setIsDragging(false);
    }
  }, [isDragging]);

  useEffect(() => {
    if (isDragging) {
      window.addEventListener('mousemove', handleMouseMove);
      window.addEventListener('mouseup', handleMouseUp);
      document.body.style.cursor = 'col-resize';
      document.body.style.userSelect = 'none';
    } else {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseup', handleMouseUp);
      document.body.style.cursor = '';
      document.body.style.userSelect = '';
    }

    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseup', handleMouseUp);
      document.body.style.cursor = '';
      document.body.style.userSelect = '';
    };
  }, [isDragging, handleMouseMove, handleMouseUp]);

  return (
    <div
      ref={containerRef}
      className="flex-1 w-full h-[calc(100vh-2.5rem)] flex flex-col md:flex-row overflow-hidden relative bg-[#0c0e12]"
    >
      {/* Left Panel */}
      <div
        style={{ width: `${leftPercent}%` }}
        className="h-full flex flex-col border-r border-[#1e232d] bg-[#0c0e12] overflow-hidden relative"
      >
        {leftPanel}
      </div>

      {/* 1px Split Handle */}
      <div
        onMouseDown={handleMouseDown}
        onDoubleClick={() => setLeftPercent(defaultLeftPercent)}
        className="hidden md:flex w-1 cursor-col-resize z-20 hover:bg-slate-600 transition-colors select-none"
        title="Double-click to reset layout"
      />

      {/* Right Panel */}
      <div
        style={{ width: `${100 - leftPercent}%` }}
        className="h-full flex flex-col bg-[#11141a] overflow-hidden relative"
      >
        {rightPanel}
      </div>
    </div>
  );
};
