import { apiClient } from './client';
import type { IngestResponse, QueryResponse, HealthResponse } from '../types/triage';

/**
 * Uploads a PDF or TXT document to the local RapidOCR/PyMuPDF parser.
 * Endpoint: POST /api/documents/ingest
 */
export async function ingestDocument(file: File): Promise<IngestResponse> {
  const formData = new FormData();
  formData.append('file', file);
  return apiClient.postFormData<IngestResponse>('api/documents/ingest', formData);
}

/**
 * Executes a clause retrieval query across the parsed document pages.
 * Endpoint: POST /api/documents/query
 */
export async function queryDocument(
  documentId: string,
  query: string
): Promise<QueryResponse> {
  return apiClient.post<QueryResponse>('api/documents/query', {
    document_id: documentId,
    query,
  });
}

/**
 * Checks backend connectivity and measures round-trip latency.
 */
export async function checkBackendPing(): Promise<{ ok: boolean; latencyMs: number; ocrEngine?: string }> {
  const start = performance.now();
  try {
    const res = await apiClient.get<HealthResponse>('api/health');
    const elapsed = Math.round(performance.now() - start);
    return { ok: res.status === 'ok', latencyMs: elapsed, ocrEngine: res.ocr_engine };
  } catch {
    return { ok: false, latencyMs: 0 };
  }
}

/**
 * Fetches the array of all past ingested documents in this session.
 * Endpoint: GET /api/documents/history
 */
export async function getDocumentsHistory(): Promise<import('../types/triage').DocumentHistoryItem[]> {
  return apiClient.get<import('../types/triage').DocumentHistoryItem[]>('api/documents/history');
}
