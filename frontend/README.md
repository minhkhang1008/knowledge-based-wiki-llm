# Knowledge Wiki Frontend

Next.js 16 App Router frontend for the Knowledge Based Wiki LLM API. It
implements the dashboard, document ingestion and management, semantic search,
and cited Q&A screens.

## Run

```bash
cp .env.example .env.local   # set NEXT_PUBLIC_API_BASE_URL
npm install
npm run dev                  # http://localhost:3000
```

The backend already allows `http://localhost:3000` via its default
`CORS_ORIGINS`, so no backend change is needed.

## Verify

```bash
npm run typecheck
npm run lint
npm run build
```

## Structure

```
src/
  app/            routes: / (Dashboard), /documents, /search, /ask
  components/
    dashboard/    StatsGrid, StatCard, QuickLinks, RecentArticles
    layout/       AppShell, Sidebar, ConnectionBadge, ThemeToggle
    theme/        ThemeProvider (light/dark, persisted)
    ui/           Button, Skeleton, ErrorState, Icons, accessible Modal
  lib/
    api/          client, errors, stats, health, articles, search, qa
    hooks/        useAsyncResource, useHealthPing
  types/api.ts    response contracts
```

## Runtime contract notes

- Metrics come from `GET /api/stats`: `total_articles`,
  `total_indexed_chunks`, `total_qa_logs`. No fallback numbers are ever
  rendered; a failure shows an error panel with retry.
- `GET /health` drives the connection badge, polled no more than once every
  30 seconds (enforced as a floor in `useHealthPing`).
- The error parser in `lib/api/errors.ts` handles all three documented shapes:
  string `detail`, object `detail`, and the envelope's `error.detail`. It maps
  `AI_ENGINE_OFFLINE`, `AI_MODEL_NOT_FOUND`, `AI_TIMEOUT`, and
  `AI_INVALID_RESPONSE` so AI availability reads differently from an API outage.
- API origin is environment-only (`NEXT_PUBLIC_API_BASE_URL`).
- Requests are aborted on unmount via `AbortController`.
- Document uploads use the server-provided format and size limits and display
  the actual `chunk_count` returned by ingestion.
- Extracted Markdown images are loaded through the document-scoped asset API.
- Document lists are paginated; search and Q&A distinguish empty context from
  transport or AI errors.
