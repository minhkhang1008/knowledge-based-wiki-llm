"use client";

import { useCallback } from "react";
import { fetchStats } from "@/lib/api/stats";
import { listArticles } from "@/lib/api/articles";
import { useAsyncResource } from "@/lib/hooks/useAsyncResource";
import { useHealthPing } from "@/lib/hooks/useHealthPing";
import { ConnectionBadge } from "@/components/layout/ConnectionBadge";
import { StatsGrid } from "@/components/dashboard/StatsGrid";
import { QuickLinks } from "@/components/dashboard/QuickLinks";
import { RecentArticles } from "@/components/dashboard/RecentArticles";
import { ErrorState } from "@/components/ui/ErrorState";
import { Button } from "@/components/ui/Button";
import { RefreshIcon } from "@/components/ui/Icons";

/**
 * Dashboard screen.
 *
 * Contract (docs/frontend-integration.md):
 * - Renders total articles, total indexed chunks, and total QA interactions
 *   from the live `GET /api/stats` response.
 * - Never substitutes sample metrics when the API is unavailable.
 * - Provides quick links to Documents, Search, and Ask.
 */
export default function DashboardPage() {
  const { state: connectionState, checkNow } = useHealthPing();

  const statsLoader = useCallback(
    (signal: AbortSignal) => fetchStats(signal),
    [],
  );
  const articlesLoader = useCallback(
    (signal: AbortSignal) => listArticles({ limit: 5 }, signal),
    [],
  );

  const stats = useAsyncResource(statsLoader);
  const articles = useAsyncResource(articlesLoader);

  const isRefreshing = stats.isRefreshing || articles.isRefreshing;

  const reloadAll = () => {
    stats.reload();
    articles.reload();
    checkNow();
  };

  return (
    <div className="mx-auto w-full max-w-5xl px-4 py-8 sm:px-6 lg:py-10">
      <div className="animate-fade-up">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
          <div className="min-w-0">
            <h1 className="text-2xl font-semibold tracking-tight text-ink sm:text-3xl">
              Dashboard
            </h1>
            <p className="mt-1.5 text-sm text-muted">
              Live status of your knowledge base, straight from the API.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <ConnectionBadge state={connectionState} />
            <Button
              onClick={reloadAll}
              disabled={isRefreshing}
              aria-label="Refresh dashboard data"
            >
              <RefreshIcon
                className={`h-4 w-4 ${isRefreshing ? "animate-spin" : ""}`}
              />
              {isRefreshing ? "Refreshing…" : "Refresh"}
            </Button>
          </div>
        </div>

        <div className="mt-8">
          {stats.status === "error" && stats.error ? (
            <ErrorState
              title="Statistics are unavailable"
              error={stats.error}
              onRetry={stats.reload}
              isRetrying={stats.isRefreshing}
            />
          ) : (
            <StatsGrid
              stats={stats.data}
              isLoading={stats.status === "loading"}
              isUnavailable={false}
            />
          )}
        </div>

        <QuickLinks />

        <RecentArticles
          articles={articles.data}
          isLoading={articles.status === "loading"}
          error={articles.status === "error" ? articles.error : null}
        />
      </div>
    </div>
  );
}
