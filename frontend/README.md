# Knowledge Wiki — Frontend

Next.js 14 (App Router) frontend for the Knowledge Based Wiki LLM API.
This drop implements the **Dashboard** screen from `docs/frontend-integration.md`.

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
    ui/           Button, Skeleton, ErrorState, Icons
  lib/
    api/          client, errors, stats, health, articles
    hooks/        useAsyncResource, useHealthPing
  types/api.ts    response contracts
```

## Dashboard contract notes

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

## Not in this drop

`/documents`, `/search`, and `/ask` are placeholders so Dashboard navigation
resolves. Build them on the same `src/lib/api` layer.
