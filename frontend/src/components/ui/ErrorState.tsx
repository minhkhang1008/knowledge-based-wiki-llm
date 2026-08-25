"use client";

import type { ApiError } from "@/lib/api/errors";
import { AlertIcon, RefreshIcon } from "./Icons";
import { Button } from "./Button";

interface ErrorStateProps {
  title: string;
  error: ApiError;
  onRetry?: () => void;
  isRetrying?: boolean;
}

/**
 * Server/network failure surface. Never renders placeholder metrics in place
 * of live data, per the integration contract.
 */
export function ErrorState({
  title,
  error,
  onRetry,
  isRetrying = false,
}: ErrorStateProps) {
  const isAi = error.isAiUnavailable;

  return (
    <div
      role="alert"
      className="rounded-2xl border border-line bg-elevated p-6"
    >
      <div className="flex items-start gap-3">
        <AlertIcon
          className={`mt-0.5 h-5 w-5 shrink-0 ${isAi ? "text-warning" : "text-danger"}`}
        />
        <div className="min-w-0 flex-1">
          <h3 className="text-sm font-semibold text-ink">{title}</h3>
          <p className="mt-1 text-sm text-muted">{error.message}</p>

          {isAi ? (
            <p className="mt-2 text-xs text-faint">
              The API itself responded. This is an AI availability problem, not a
              general API outage.
            </p>
          ) : null}

          {error.code || error.status ? (
            <p className="mt-2 font-mono text-xs text-faint">
              {[error.status ? `HTTP ${error.status}` : null, error.code]
                .filter(Boolean)
                .join(" · ")}
            </p>
          ) : null}

          {onRetry && error.isRetryable !== false ? (
            <Button
              onClick={onRetry}
              disabled={isRetrying}
              className="mt-4"
              aria-label="Retry loading"
            >
              <RefreshIcon
                className={`h-4 w-4 ${isRetrying ? "animate-spin" : ""}`}
              />
              {isRetrying ? "Retrying…" : "Retry"}
            </Button>
          ) : null}
        </div>
      </div>
    </div>
  );
}
