import { useState, useCallback } from 'react';
import type { Citation } from '../types/triage';

export interface UsePdfNavigationReturn {
  currentPage: number;
  activeCitation: Citation | null;
  jumpToCitation: (citation: Citation) => void;
  jumpToPage: (page: number) => void;
  clearActiveCitation: () => void;
}

export function usePdfNavigation(initialPage: number = 1): UsePdfNavigationReturn {
  const [currentPage, setCurrentPage] = useState<number>(initialPage);
  const [activeCitation, setActiveCitation] = useState<Citation | null>(null);

  const jumpToCitation = useCallback((citation: Citation) => {
    setActiveCitation(citation);
    setCurrentPage(citation.page);
  }, []);

  const jumpToPage = useCallback((page: number) => {
    setCurrentPage(page);
    setActiveCitation(null);
  }, []);

  const clearActiveCitation = useCallback(() => {
    setActiveCitation(null);
  }, []);

  return {
    currentPage,
    activeCitation,
    jumpToCitation,
    jumpToPage,
    clearActiveCitation,
  };
}
