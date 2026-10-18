import { useState, useCallback } from 'react';
import { ingestDocument } from '../api/documents';
import type { IngestResponse } from '../types/triage';

export interface UseDocumentReturn {
  file: File | null;
  ingestData: IngestResponse | null;
  isUploading: boolean;
  uploadError: string | null;
  handleFileSelect: (file: File) => Promise<IngestResponse | null>;
  resetDocument: () => void;
}

export function useDocument(): UseDocumentReturn {
  const [file, setFile] = useState<File | null>(null);
  const [ingestData, setIngestData] = useState<IngestResponse | null>(null);
  const [isUploading, setIsUploading] = useState<boolean>(false);
  const [uploadError, setUploadError] = useState<string | null>(null);

  const handleFileSelect = useCallback(async (selectedFile: File): Promise<IngestResponse | null> => {
    setIsUploading(true);
    setUploadError(null);
    setFile(selectedFile);

    try {
      const response = await ingestDocument(selectedFile);
      setIngestData(response);
      setIsUploading(false);
      return response;
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Ingest request failed';
      setUploadError(msg);

      // Client-side fallback so file is still readable locally if server is offline
      const fallback: IngestResponse = {
        document_id: `local-${Date.now()}`,
        filename: selectedFile.name,
        total_pages: 1,
        pages: [
          {
            page_number: 1,
            text: '',
            ocr_applied: false,
            char_count: 0,
          },
        ],
      };
      setIngestData(fallback);
      setIsUploading(false);
      return fallback;
    }
  }, []);

  const resetDocument = useCallback(() => {
    setFile(null);
    setIngestData(null);
    setIsUploading(false);
    setUploadError(null);
  }, []);

  return {
    file,
    ingestData,
    isUploading,
    uploadError,
    handleFileSelect,
    resetDocument,
  };
}
