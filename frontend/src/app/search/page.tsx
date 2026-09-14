"use client";

import { useEffect, useRef, useState, type FormEvent } from "react";
import { semanticSearch } from "@/lib/api/search";
import { errorMessage } from "@/lib/api/errors";
import type { SourceChunk } from "@/types/api";
import { Button } from "@/components/ui/Button";
import { DocumentsIcon, SearchIcon } from "@/components/ui/Icons";

export default function SearchPage() {
  const [query, setQuery] = useState("");
  const [submittedQuery, setSubmittedQuery] = useState("");
  const [results, setResults] = useState<SourceChunk[]>([]);
  const [hasSearched, setHasSearched] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");
  const requestRef = useRef<AbortController | null>(null);

  useEffect(() => () => requestRef.current?.abort(), []);

  async function runSearch() {
    const normalizedQuery = query.trim();
    if (normalizedQuery.length < 2) {
      setError("Enter at least 2 characters.");
      return;
    }

    requestRef.current?.abort();
    const controller = new AbortController();
    requestRef.current = controller;
    try {
      setIsLoading(true);
      setError("");
      setSubmittedQuery(normalizedQuery);
      setResults(await semanticSearch(normalizedQuery, controller.signal));
      setHasSearched(true);
    } catch (cause) {
      if (!controller.signal.aborted) {
        setResults([]);
        setHasSearched(true);
        setError(errorMessage(cause));
      }
    } finally {
      if (requestRef.current === controller) setIsLoading(false);
    }
  }

  function handleSearch(event: FormEvent) {
    event.preventDefault();
    void runSearch();
  }

  return (
    <div className="mx-auto w-full max-w-5xl px-4 py-8 sm:px-6 lg:py-10">
      <header>
        <h1 className="text-2xl font-semibold tracking-tight text-ink sm:text-3xl">
          Semantic search
        </h1>
        <p className="mt-1.5 max-w-2xl text-sm leading-6 text-muted">
          Search by meaning across every indexed chunk, with source and page
          context preserved.
        </p>
      </header>

      <form onSubmit={handleSearch} className="mt-7 flex max-w-3xl flex-col gap-3 sm:flex-row">
        <div className="relative min-w-0 flex-1">
          <label htmlFor="semantic-query" className="sr-only">Search the knowledge base</label>
          <SearchIcon className="pointer-events-none absolute left-3.5 top-1/2 h-5 w-5 -translate-y-1/2 text-muted" aria-hidden="true" />
          <input
            id="semantic-query"
            type="search"
            value={query}
            onChange={(event) => {
              setQuery(event.target.value);
              setError("");
            }}
            placeholder="What does the handbook say about leave?"
            className="h-11 w-full rounded-xl border border-line bg-surface pl-11 pr-4 text-sm text-ink shadow-sm placeholder:text-faint"
            aria-describedby={error ? "search-error" : undefined}
          />
        </div>
        <Button type="submit" variant="primary" className="h-11 px-6" disabled={isLoading || query.trim().length < 2}>
          <SearchIcon className="h-4 w-4" aria-hidden="true" />
          {isLoading ? "Searching..." : "Search"}
        </Button>
      </form>

      {error ? (
        <div id="search-error" role="alert" className="mt-5 rounded-xl border border-danger/30 bg-danger/10 p-4 text-sm text-danger">
          <p>{error}</p>
          {hasSearched ? (
            <button type="button" className="mt-2 font-medium underline" onClick={() => void runSearch()}>
              Retry search
            </button>
          ) : null}
        </div>
      ) : null}

      <section className="mt-8" aria-live="polite" aria-busy={isLoading}>
        {isLoading ? (
          <div className="space-y-3" aria-label="Searching documents">
            {[0, 1, 2].map((item) => (
              <div key={item} className="h-32 animate-pulse rounded-xl bg-hover" />
            ))}
          </div>
        ) : hasSearched && results.length === 0 && !error ? (
          <div className="flex min-h-60 flex-col items-center justify-center rounded-xl border border-dashed border-line px-6 text-center">
            <DocumentsIcon className="h-9 w-9 text-faint" aria-hidden="true" />
            <h2 className="mt-3 text-base font-semibold text-ink">No relevant passages</h2>
            <p className="mt-1 max-w-md text-sm leading-6 text-muted">
              No indexed chunk met the relevance threshold for “{submittedQuery}”. Try a broader phrase.
            </p>
          </div>
        ) : results.length > 0 ? (
          <div>
            <div className="mb-4 flex items-baseline justify-between gap-4">
              <h2 className="text-base font-semibold text-ink">Results</h2>
              <span className="font-mono text-xs text-muted">
                {results.length} {results.length === 1 ? "passage" : "passages"}
              </span>
            </div>
            <ol className="space-y-3">
              {results.map((result, index) => (
                <li key={`${result.article_id ?? "unknown"}-${index}`} className="rounded-xl border border-line bg-surface p-5 shadow-sm">
                  <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-muted">
                    <span className="font-mono text-ink">S{index + 1}</span>
                    <span>{result.source_file ?? "Unknown source"}</span>
                    {result.page_number !== null ? <span>Page {result.page_number}</span> : null}
                    {result.distance !== null ? <span>Distance {result.distance.toFixed(3)}</span> : null}
                  </div>
                  <p className="mt-3 whitespace-pre-wrap text-sm leading-6 text-ink">{result.text}</p>
                </li>
              ))}
            </ol>
          </div>
        ) : (
          <div className="rounded-xl border border-line bg-surface px-6 py-10">
            <h2 className="text-sm font-semibold text-ink">Search indexed content</h2>
            <p className="mt-1 max-w-xl text-sm leading-6 text-muted">
              Use a question or concept. Results are ranked by vector distance rather than exact keyword matches.
            </p>
          </div>
        )}
      </section>
    </div>
  );
}
