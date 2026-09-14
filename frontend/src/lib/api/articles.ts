import type { Article, SupportedFormatsData } from "@/types/api";
import { requestEnvelope } from "./client";

/** GET /api/v1/articles/supported-formats */
export function fetchSupportedFormats(
  signal?: AbortSignal,
): Promise<SupportedFormatsData> {
  return requestEnvelope<SupportedFormatsData>(
    "/api/v1/articles/supported-formats",
    { signal },
  );
}

export interface ListArticlesParams {
  skip?: number;
  /** The API caps this at 100. */
  limit?: number;
  search?: string;
}

/** GET /api/articles */
export function listArticles(
  params: ListArticlesParams = {},
  signal?: AbortSignal,
): Promise<Article[]> {
  const query = new URLSearchParams();
  query.set("skip", String(params.skip ?? 0));
  query.set("limit", String(Math.min(params.limit ?? 20, 100)));
  if (params.search && params.search.trim() !== "") {
    query.set("search", params.search.trim());
  }
  return requestEnvelope<Article[]>(`/api/articles?${query.toString()}`, {
    signal,
  });
}

/** POST /api/v1/articles/upload */
export function uploadArticle(
  formData: FormData,
  signal?: AbortSignal,
): Promise<{ id: string; chunks_created: number; message: string }> {
  return requestEnvelope<{ id: string; chunks_created: number; message: string }>(
    "/api/v1/articles/upload",
    {
      method: "POST",
      formData,
      signal,
    }
  );
}

/** GET /api/articles/{article_id} */
export function getArticle(
  articleId: string,
  signal?: AbortSignal,
): Promise<Article> {
  return requestEnvelope<Article>(`/api/articles/${articleId}`, { signal });
}

/** DELETE /api/articles/{article_id} */
export function deleteArticle(
  articleId: string,
  signal?: AbortSignal,
): Promise<{ message: string }> {
  return requestEnvelope<{ message: string }>(`/api/articles/${articleId}`, {
    method: "DELETE",
    signal,
  });
}
