"use client";

import Link from "next/link";
import type { Article } from "@/types/api";
import type { ApiError } from "@/lib/api/errors";
import { Skeleton } from "@/components/ui/Skeleton";
import { ArrowRightIcon, DocumentsIcon } from "@/components/ui/Icons";

interface RecentArticlesProps {
  articles: Article[] | null;
  isLoading: boolean;
  error: ApiError | null;
}

/** Formats an ISO timestamp, tolerating a missing timezone suffix. */
function formatUpdatedAt(value: string): string {
  const normalised = /[Zz]|[+-]\d{2}:\d{2}$/.test(value) ? value : `${value}Z`;
  const date = new Date(normalised);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat("en-US", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(date);
}

/** Derives the file extension shown as the format tag. */
function formatTag(sourceFile: string): string {
  const dot = sourceFile.lastIndexOf(".");
  return dot === -1 ? "file" : sourceFile.slice(dot + 1).toLowerCase();
}

export function RecentArticles({
  articles,
  isLoading,
  error,
}: RecentArticlesProps) {
  return (
    <section aria-labelledby="recent-heading" className="mt-10">
      <div className="flex items-center justify-between gap-3">
        <h2 id="recent-heading" className="text-sm font-semibold text-ink">
          Recently updated
        </h2>
        <Link
          href="/documents"
          className="inline-flex items-center gap-1 rounded-lg px-2 py-1 text-xs font-medium text-muted transition-colors hover:bg-hover hover:text-ink"
        >
          View all documents
          <ArrowRightIcon className="h-3.5 w-3.5" />
        </Link>
      </div>

      <div className="mt-3 overflow-hidden rounded-2xl border border-line bg-elevated">
        {isLoading ? (
          <ul className="divide-y divide-line">
            {[0, 1, 2].map((row) => (
              <li key={row} className="flex items-center gap-3 px-4 py-3.5">
                <Skeleton className="h-8 w-8 rounded-full" />
                <div className="flex-1 space-y-2">
                  <Skeleton className="h-3.5 w-1/2" />
                  <Skeleton className="h-3 w-1/3" />
                </div>
              </li>
            ))}
          </ul>
        ) : error ? (
          // A secondary panel failing must not block the metrics above.
          <p className="px-4 py-6 text-sm text-muted">
            The article list could not be loaded. {error.message}
          </p>
        ) : articles && articles.length > 0 ? (
          <ul className="divide-y divide-line">
            {articles.map((article) => (
              <li key={article.id}>
                <Link
                  href="/documents"
                  className="flex items-center gap-3 px-4 py-3.5 transition-colors hover:bg-hover"
                >
                  <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-surface text-muted">
                    <DocumentsIcon className="h-4 w-4" />
                  </span>
                  <span className="min-w-0 flex-1">
                    <span className="block truncate text-sm font-medium text-ink">
                      {article.title}
                    </span>
                    <span className="block truncate text-xs text-faint">
                      {article.source_file} · updated{" "}
                      {formatUpdatedAt(article.updated_at)}
                    </span>
                  </span>
                  <span className="shrink-0 rounded-full border border-line px-2 py-0.5 font-mono text-[11px] uppercase text-muted">
                    {formatTag(article.source_file)}
                  </span>
                </Link>
              </li>
            ))}
          </ul>
        ) : (
          <div className="px-4 py-10 text-center">
            <p className="text-sm font-medium text-ink">
              No articles in the knowledge base yet
            </p>
            <p className="mx-auto mt-1 max-w-sm text-sm text-muted">
              Upload a supported document on the Documents page to build the
              index, then search or ask questions about it.
            </p>
            <Link
              href="/documents"
              className="mt-4 inline-flex items-center gap-2 rounded-full bg-ink px-4 py-2 text-sm font-medium text-canvas transition-opacity hover:opacity-90"
            >
              Upload a document
              <ArrowRightIcon className="h-4 w-4" />
            </Link>
          </div>
        )}
      </div>
    </section>
  );
}
