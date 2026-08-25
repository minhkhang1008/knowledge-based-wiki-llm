"use client";

import type { ComponentType, SVGProps } from "react";
import { Skeleton } from "@/components/ui/Skeleton";

interface StatCardProps {
  label: string;
  hint: string;
  value: number | null;
  isLoading: boolean;
  /** True when the value could not be read from the API. */
  isUnavailable: boolean;
  icon: ComponentType<SVGProps<SVGSVGElement>>;
}

/** Formats an integer with locale grouping. Never invents a value. */
function formatCount(value: number): string {
  return new Intl.NumberFormat("en-US").format(value);
}

export function StatCard({
  label,
  hint,
  value,
  isLoading,
  isUnavailable,
  icon: Icon,
}: StatCardProps) {
  return (
    <div className="rounded-2xl border border-line bg-elevated p-5 transition-colors hover:border-faint/60">
      <div className="flex items-center justify-between gap-3">
        <p className="text-sm font-medium text-muted">{label}</p>
        <span className="flex h-8 w-8 items-center justify-center rounded-full bg-surface text-muted">
          <Icon className="h-[18px] w-[18px]" />
        </span>
      </div>

      <div className="mt-4 min-h-[44px]">
        {isLoading ? (
          <Skeleton className="h-9 w-24" />
        ) : isUnavailable || value === null ? (
          <p className="text-2xl font-medium text-faint" aria-live="polite">
            Unavailable
          </p>
        ) : (
          <p className="text-3xl font-semibold tracking-tight text-ink tabular-nums">
            {formatCount(value)}
          </p>
        )}
      </div>

      <p className="mt-2 text-xs text-faint">
        {isUnavailable ? "Live value could not be read from the API." : hint}
      </p>
    </div>
  );
}
