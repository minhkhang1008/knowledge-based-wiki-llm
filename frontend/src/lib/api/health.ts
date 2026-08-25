import type { HealthData } from "@/types/api";
import { request } from "./client";

/**
 * GET /health -> `{"status":"ok"}`.
 * This route does not use the envelope.
 */
export function fetchHealth(signal?: AbortSignal): Promise<HealthData> {
  return request<HealthData>("/health", { signal, timeoutMs: 8_000 });
}
