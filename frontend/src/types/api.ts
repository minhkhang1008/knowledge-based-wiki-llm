/**
 * Response contracts mirrored from the FastAPI backend.
 * Source of truth: docs/frontend-integration.md and api/app/schemas.
 */

/** Standard success/error envelope used by every main endpoint. */
export interface ApiEnvelope<T> {
  success: boolean;
  data: T | null;
  message: string;
  error: ApiErrorFormat | null;
}

/** `error` object inside the envelope (app/schemas/ErrorFormat.py). */
export interface ApiErrorFormat {
  code: string;
  detail: string;
}

/** GET /api/stats -> data */
export interface StatsData {
  total_articles: number;
  total_qa_logs: number;
  total_indexed_chunks: number;
}

/** GET /health */
export interface HealthData {
  status: string;
}

/** GET /api/v1/articles/supported-formats -> data */
export interface SupportedFormatsData {
  extensions: string[];
  max_upload_size_mb: number;
}

/** Article record returned by /api/articles endpoints. */
export interface Article {
  id: string;
  document_id: string;
  title: string;
  content: string;
  source_file: string;
  created_at: string;
  updated_at: string;
}

/** A retrieved chunk, shared by search results and QA sources. */
export interface SourceChunk {
  text: string;
  article_id: string;
  source_file: string;
  page_number: number | null;
  distance: number | null;
}
