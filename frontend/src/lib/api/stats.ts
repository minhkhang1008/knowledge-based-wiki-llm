import type { StatsData } from "@/types/api";
import { requestEnvelope } from "./client";

/** GET /api/stats */
export function fetchStats(signal?: AbortSignal): Promise<StatsData> {
  return requestEnvelope<StatsData>("/api/stats", { signal });
}
