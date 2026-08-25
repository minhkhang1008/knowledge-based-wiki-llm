/**
 * Error normalisation for the backend's three error shapes:
 *   1. `{ detail: "string" }`
 *   2. `{ detail: { ... } }`
 *   3. the standard envelope with `error.code` / `error.detail`
 */

export type ApiErrorKind =
  | "network"
  | "timeout"
  | "validation"
  | "not_found"
  | "ai_offline"
  | "ai_model_missing"
  | "ai_timeout"
  | "ai_invalid"
  | "conflict"
  | "payload_too_large"
  | "unsupported_media"
  | "unprocessable"
  | "server"
  | "unknown";

export class ApiError extends Error {
  readonly status: number | null;
  readonly code: string | null;
  readonly detail: string | null;
  readonly kind: ApiErrorKind;

  constructor(init: {
    message: string;
    status?: number | null;
    code?: string | null;
    detail?: string | null;
    kind: ApiErrorKind;
  }) {
    super(init.message);
    this.name = "ApiError";
    this.status = init.status ?? null;
    this.code = init.code ?? null;
    this.detail = init.detail ?? null;
    this.kind = init.kind;
  }

  /** True when the backend is reachable but the AI engine is not. */
  get isAiUnavailable(): boolean {
    return (
      this.kind === "ai_offline" ||
      this.kind === "ai_model_missing" ||
      this.kind === "ai_timeout" ||
      this.kind === "ai_invalid"
    );
  }

  /** True when retrying the same request could reasonably succeed. */
  get isRetryable(): boolean {
    return (
      this.kind === "network" ||
      this.kind === "timeout" ||
      this.kind === "server" ||
      this.kind === "ai_timeout" ||
      this.kind === "ai_invalid" ||
      this.kind === "ai_offline"
    );
  }
}

function kindFromStatusAndCode(
  status: number | null,
  code: string | null,
): ApiErrorKind {
  switch (code) {
    case "AI_ENGINE_OFFLINE":
      return "ai_offline";
    case "AI_MODEL_NOT_FOUND":
      return "ai_model_missing";
    case "AI_TIMEOUT":
      return "ai_timeout";
    case "AI_INVALID_RESPONSE":
      return "ai_invalid";
    case "VALIDATION_ERROR":
      return "validation";
    case "DUPLICATE_DOCUMENT":
      return "conflict";
    default:
      break;
  }

  switch (status) {
    case 404:
      return "not_found";
    case 409:
      return "conflict";
    case 413:
      return "payload_too_large";
    case 415:
      return "unsupported_media";
    case 422:
      return "unprocessable";
    case 502:
      return "ai_invalid";
    case 503:
      return "ai_offline";
    case 504:
      return "ai_timeout";
    default:
      if (status !== null && status >= 500) return "server";
      if (status !== null && status >= 400) return "unknown";
      return "unknown";
  }
}

/** Human-readable English copy for each failure kind. */
const FALLBACK_MESSAGE: Record<ApiErrorKind, string> = {
  network: "Could not reach the API. Check that the backend is running.",
  timeout: "The request took too long and was cancelled.",
  validation: "The request was rejected as invalid.",
  not_found: "The requested resource does not exist.",
  ai_offline: "Ollama is not available. Start Ollama and try again.",
  ai_model_missing:
    "The configured Ollama model is not installed. Pull the model and try again.",
  ai_timeout: "The AI request timed out.",
  ai_invalid: "The AI returned an invalid response.",
  conflict: "This document already exists in the knowledge base.",
  payload_too_large: "The file is larger than the configured upload limit.",
  unsupported_media: "This file format is not supported yet.",
  unprocessable: "No usable content could be extracted from that file.",
  server: "The server hit an unexpected error.",
  unknown: "The request failed.",
};

/** Pulls a usable message out of any of the documented error bodies. */
function readErrorBody(body: unknown): { message: string | null; code: string | null; detail: string | null } {
  if (typeof body === "string" && body.trim() !== "") {
    return { message: body, code: null, detail: body };
  }
  if (body === null || typeof body !== "object") {
    return { message: null, code: null, detail: null };
  }

  const record = body as Record<string, unknown>;

  // Shape 3: standard envelope.
  const envelopeError = record.error;
  if (envelopeError && typeof envelopeError === "object") {
    const errorRecord = envelopeError as Record<string, unknown>;
    const code = typeof errorRecord.code === "string" ? errorRecord.code : null;
    const detail =
      typeof errorRecord.detail === "string" ? errorRecord.detail : null;
    const message =
      typeof record.message === "string" && record.message.trim() !== ""
        ? record.message
        : detail;
    return { message, code, detail };
  }

  // Shapes 1 and 2: FastAPI `detail`.
  const detailValue = record.detail;
  if (typeof detailValue === "string") {
    return { message: detailValue, code: null, detail: detailValue };
  }
  if (detailValue && typeof detailValue === "object") {
    const detailRecord = detailValue as Record<string, unknown>;
    const code = typeof detailRecord.code === "string" ? detailRecord.code : null;
    const inner =
      typeof detailRecord.detail === "string"
        ? detailRecord.detail
        : typeof detailRecord.message === "string"
          ? detailRecord.message
          : null;
    return { message: inner, code, detail: inner ?? JSON.stringify(detailValue) };
  }

  if (typeof record.message === "string" && record.message.trim() !== "") {
    return { message: record.message, code: null, detail: null };
  }

  return { message: null, code: null, detail: null };
}

/** Builds an ApiError from an HTTP response body. */
export function toApiError(status: number, body: unknown): ApiError {
  const { message, code, detail } = readErrorBody(body);
  const kind = kindFromStatusAndCode(status, code);
  return new ApiError({
    message: message ?? FALLBACK_MESSAGE[kind],
    status,
    code,
    detail,
    kind,
  });
}

/** Wraps a thrown fetch/abort failure. */
export function toTransportError(cause: unknown): ApiError {
  if (cause instanceof ApiError) return cause;
  if (cause instanceof DOMException && cause.name === "AbortError") {
    return new ApiError({ message: FALLBACK_MESSAGE.timeout, kind: "timeout" });
  }
  return new ApiError({
    message: FALLBACK_MESSAGE.network,
    kind: "network",
    detail: cause instanceof Error ? cause.message : null,
  });
}

/** Safe message extraction for any caught value. */
export function errorMessage(cause: unknown): string {
  if (cause instanceof ApiError) return cause.message;
  if (cause instanceof Error) return cause.message;
  return FALLBACK_MESSAGE.unknown;
}
