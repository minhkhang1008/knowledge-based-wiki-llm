import type { ApiEnvelope } from "@/types/api";
import { ApiError, toApiError, toTransportError } from "./errors";

/** API origin comes from the environment only. Never hardcode it in views. */
export const API_BASE_URL = (
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000"
).replace(/\/+$/, "");

interface RequestOptions {
  method?: "GET" | "POST" | "PUT" | "DELETE";
  /** JSON body. Omit for FormData or GET. */
  json?: unknown;
  /** FormData body. Content-Type is intentionally left to the browser. */
  formData?: FormData;
  signal?: AbortSignal;
  /** Client-side timeout in ms. Set to 0 to disable. */
  timeoutMs?: number;
}

const DEFAULT_TIMEOUT_MS = 30_000;

/** Merges an external signal with an internal timeout signal. */
function withTimeout(
  signal: AbortSignal | undefined,
  timeoutMs: number,
): { signal: AbortSignal | undefined; cleanup: () => void } {
  if (timeoutMs <= 0) return { signal, cleanup: () => undefined };

  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  const onAbort = () => controller.abort();
  signal?.addEventListener("abort", onAbort, { once: true });

  return {
    signal: controller.signal,
    cleanup: () => {
      clearTimeout(timer);
      signal?.removeEventListener("abort", onAbort);
    },
  };
}

async function parseBody(response: Response): Promise<unknown> {
  const contentType = response.headers.get("content-type") ?? "";
  try {
    if (contentType.includes("application/json")) return await response.json();
    const text = await response.text();
    return text === "" ? null : text;
  } catch {
    return null;
  }
}

/** Performs a request and returns the raw parsed body. */
export async function request<T>(
  path: string,
  options: RequestOptions = {},
): Promise<T> {
  const {
    method = "GET",
    json,
    formData,
    signal,
    timeoutMs = DEFAULT_TIMEOUT_MS,
  } = options;

  const headers: Record<string, string> = { Accept: "application/json" };
  let body: BodyInit | undefined;

  if (formData) {
    // Do not set Content-Type: the browser must add the multipart boundary.
    body = formData;
  } else if (json !== undefined) {
    headers["Content-Type"] = "application/json";
    body = JSON.stringify(json);
  }

  const timeout = withTimeout(signal, timeoutMs);

  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      method,
      headers,
      body,
      signal: timeout.signal,
      cache: "no-store",
    });
  } catch (cause) {
    throw toTransportError(cause);
  } finally {
    timeout.cleanup();
  }

  const parsed = await parseBody(response);

  if (!response.ok) {
    throw toApiError(response.status, parsed);
  }

  return parsed as T;
}

/**
 * Performs a request that returns the team envelope and unwraps `data`.
 * A `success: false` envelope with HTTP 200 is still treated as a failure.
 */
export async function requestEnvelope<T>(
  path: string,
  options: RequestOptions = {},
): Promise<T> {
  const envelope = await request<ApiEnvelope<T>>(path, options);

  if (envelope === null || typeof envelope !== "object") {
    throw new ApiError({
      message: "The API returned an unreadable response.",
      kind: "server",
    });
  }

  if (envelope.success === false || envelope.data === null) {
    throw toApiError(200, envelope);
  }

  return envelope.data;
}
