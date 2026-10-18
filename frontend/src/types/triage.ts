export interface PageData {
  page_number: number;
  text: string;
  ocr_applied: boolean;
  char_count: number;
}

export interface IngestResponse {
  document_id: string;
  filename: string;
  total_pages: number;
  pages: PageData[];
}

export interface QueryRequest {
  document_id: string;
  query: string;
}

export interface Citation {
  page: number;
  quote: string;
}

export interface QueryResponse {
  answer: string;
  citations: Citation[];
  explicit_terms: string[];
  potential_concerns: string[];
  uncertainties: string[];
  model_ready: boolean;
}

export interface HealthResponse {
  status: string;
  ocr_engine: string;
}

export interface DocumentHistoryItem {
  document_id: string;
  filename: string;
  total_pages: number;
  digital_pages: number;
  ocr_pages: number;
  timestamp: string;
  total_chars: number;
}
