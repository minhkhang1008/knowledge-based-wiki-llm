"use client";

import type { ConnectionState } from "@/lib/hooks/useHealthPing";

const LABEL: Record<ConnectionState, string> = {
  checking: "Checking API",
  online: "API connected",
  offline: "API unreachable",
};

const DOT: Record<ConnectionState, string> = {
  checking: "bg-faint",
  online: "bg-emerald-500",
  offline: "bg-danger",
};

/** Optional connection indicator driven by GET /health. */
export function ConnectionBadge({ state }: { state: ConnectionState }) {
  return (
    <span
      className="inline-flex items-center gap-2 rounded-full border border-line bg-elevated px-3 py-1.5 text-xs font-medium text-muted"
      role="status"
      aria-live="polite"
    >
      <span className={`h-2 w-2 rounded-full ${DOT[state]}`} aria-hidden="true" />
      {LABEL[state]}
    </span>
  );
}
