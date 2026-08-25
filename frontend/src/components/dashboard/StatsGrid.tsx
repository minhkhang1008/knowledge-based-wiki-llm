"use client";

import type { StatsData } from "@/types/api";
import {
  ChunksIcon,
  ConversationIcon,
  DocumentsIcon,
} from "@/components/ui/Icons";
import { StatCard } from "./StatCard";

interface StatsGridProps {
  stats: StatsData | null;
  isLoading: boolean;
  isUnavailable: boolean;
}

/** The three live metrics required on the Dashboard by the integration doc. */
export function StatsGrid({ stats, isLoading, isUnavailable }: StatsGridProps) {
  return (
    <section aria-labelledby="stats-heading">
      <h2 id="stats-heading" className="sr-only">
        Knowledge base statistics
      </h2>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <StatCard
          label="Total articles"
          hint="Documents converted to Markdown and stored in SQLite."
          value={stats?.total_articles ?? null}
          isLoading={isLoading}
          isUnavailable={isUnavailable}
          icon={DocumentsIcon}
        />
        <StatCard
          label="Indexed chunks"
          hint="Embedded passages available to search and QA in Chroma."
          value={stats?.total_indexed_chunks ?? null}
          isLoading={isLoading}
          isUnavailable={isUnavailable}
          icon={ChunksIcon}
        />
        <StatCard
          label="QA interactions"
          hint="Questions answered against the knowledge base so far."
          value={stats?.total_qa_logs ?? null}
          isLoading={isLoading}
          isUnavailable={isUnavailable}
          icon={ConversationIcon}
        />
      </div>
    </section>
  );
}
