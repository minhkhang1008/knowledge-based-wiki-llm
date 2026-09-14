import type { SearchData, SourceChunk } from "@/types/api";
import { requestEnvelope } from "./client";

export async function semanticSearch(
  query: string,
  signal?: AbortSignal,
): Promise<SourceChunk[]> {
  const data = await requestEnvelope<SearchData>("/api/search", {
    method: "POST",
    json: { query },
    signal,
  });
  return data.results ?? [];
}
