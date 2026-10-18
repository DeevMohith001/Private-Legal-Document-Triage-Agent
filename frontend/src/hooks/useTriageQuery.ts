import { useState, useCallback } from 'react';
import { queryDocument } from '../api/documents';
import type { QueryResponse } from '../types/triage';

export interface UseTriageQueryReturn {
  isLoading: boolean;
  error: string | null;
  activeQuery: string | null;
  activeResponse: QueryResponse | null;
  submitQuery: (documentId: string, query: string) => Promise<QueryResponse | null>;
  resetQuery: () => void;
}

export function useTriageQuery(): UseTriageQueryReturn {
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [activeQuery, setActiveQuery] = useState<string | null>(null);
  const [activeResponse, setActiveResponse] = useState<QueryResponse | null>(null);

  const submitQuery = useCallback(
    async (documentId: string, query: string): Promise<QueryResponse | null> => {
      setIsLoading(true);
      setError(null);
      setActiveQuery(query);

      try {
        const response = await queryDocument(documentId, query);
        setActiveResponse(response);
        setIsLoading(false);
        return response;
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : 'Query failed';
        setError(msg);
        setIsLoading(false);
        return null;
      }
    },
    []
  );

  const resetQuery = useCallback(() => {
    setActiveQuery(null);
    setActiveResponse(null);
    setError(null);
    setIsLoading(false);
  }, []);

  return {
    isLoading,
    error,
    activeQuery,
    activeResponse,
    submitQuery,
    resetQuery,
  };
}
