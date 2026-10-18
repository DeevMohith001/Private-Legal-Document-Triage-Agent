import React, { useRef, useState } from 'react';
import { FileText, Loader2 } from 'lucide-react';

interface DropzoneProps {
  onFileSelect: (file: File) => void;
  isUploading?: boolean;
  uploadError?: string | null;
}

export const Dropzone: React.FC<DropzoneProps> = ({
  onFileSelect,
  isUploading = false,
  uploadError,
}) => {
  const [isDragOver, setIsDragOver] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);

    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      validateAndUpload(e.dataTransfer.files[0]);
    }
  };

  const handleFileInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      validateAndUpload(e.target.files[0]);
    }
  };

  const validateAndUpload = (file: File) => {
    const valid = ['.pdf', '.txt'].some((ext) => file.name.toLowerCase().endsWith(ext));
    if (!valid) {
      alert('Only .pdf or .txt documents are supported.');
      return;
    }
    onFileSelect(file);
  };

  return (
    <div className="h-full w-full flex items-center justify-center p-6 bg-[#0c0e12] select-none">
      <input
        ref={fileInputRef}
        type="file"
        accept=".pdf,.txt,application/pdf,text/plain"
        onChange={handleFileInputChange}
        className="hidden"
      />

      <div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        className={`w-full max-w-sm p-6 rounded-lg border border-dashed transition-colors flex flex-col items-center text-center ${
          isDragOver
            ? 'border-slate-300 bg-[#161a22]'
            : 'border-[#1e232d] bg-[#11141a]/60 hover:border-slate-500'
        }`}
      >
        <div className="w-10 h-10 rounded-md bg-[#161a22] border border-[#1e232d] flex items-center justify-center text-slate-300 mb-3">
          <FileText className="w-5 h-5 text-slate-400" />
        </div>

        <span className="text-xs font-medium text-slate-200 mb-1">
          {isUploading ? 'Parsing document with RapidOCR...' : 'Drop contract or agreement here'}
        </span>

        <span className="text-[11px] text-slate-500 mb-4">
          Direct local text extraction & automated OCR fallback
        </span>

        <button
          type="button"
          disabled={isUploading}
          onClick={() => fileInputRef.current?.click()}
          className="h-7 px-3 text-xs font-medium text-slate-200 bg-[#161a22] hover:bg-[#1c212c] border border-[#1e232d] hover:border-slate-500 rounded transition-colors flex items-center gap-1.5 cursor-pointer disabled:opacity-50"
        >
          {isUploading && <Loader2 className="w-3 h-3 animate-spin text-slate-400" />}
          <span>Browse Files</span>
        </button>

        {uploadError && (
          <p className="mt-3 text-[11px] text-rose-400 text-center font-mono">
            {uploadError}
          </p>
        )}

        {/* Format tags */}
        <div className="mt-4 pt-3 border-t border-[#1e232d] w-full flex items-center justify-center gap-2">
          <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-[#161a22] border border-[#1e232d] text-slate-400">
            .pdf
          </span>
          <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-[#161a22] border border-[#1e232d] text-slate-400">
            .txt
          </span>
        </div>
      </div>
    </div>
  );
};
