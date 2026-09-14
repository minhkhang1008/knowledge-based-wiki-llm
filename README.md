# Knowledge Based Wiki LLM

A local-first knowledge base that converts office documents to Markdown, chunks and embeds their content, stores searchable vectors in ChromaDB, and answers questions through Ollama with source citations.

## Current status

The completed product includes:

- Article lifecycle in SQLite with ChromaDB synchronization.
- Semantic search with a calibrated distance threshold.
- RAG answers with required source citations and no-context handling.
- Document conversion and format-aware chunking for PDF, images, DOCX, XLSX,
  XLSM, and PPTX, including OCR metadata and extracted-image assets.
- One upload-to-index ingest endpoint with compensating rollback.
- Retrieval evaluation, index-integrity checks, and API tests.
- A responsive Next.js UI for dashboard metrics, document management,
  semantic search, and cited question answering.

## Quick start

Requirements:

- Python 3.11 and Node.js 20.9 or newer
- Ollama
- `nomic-embed-text`
- `llama3.2`

```bash
ollama pull nomic-embed-text
ollama pull llama3.2
python -m venv venv
source venv/bin/activate
pip install -r api/requirements-dev.txt
cp api/.env.example api/.env
cd api
uvicorn app.main:app --reload
```

In a second terminal:

```bash
cd frontend
cp .env.example .env.local
npm ci
npm run dev
```

Open `http://localhost:3000` for the product UI or
`http://localhost:8000/docs` for interactive API documentation.

## Docker Compose

The root Compose stack starts Ollama, downloads the configured embedding and
chat models, then starts the API and frontend. Model and knowledge-base data
are persisted in named volumes:

```bash
cp .env.example .env
docker compose up --build
```

The first start takes longer because Ollama downloads both models. Verify readiness with:

```bash
curl http://localhost:8000/health
curl --fail http://localhost:3000
```

## Run tests

```bash
cd api
python -m pytest -q

cd ../frontend
npm run lint
npm run typecheck
npm run build
npm audit --audit-level=high
```

The real retrieval baseline requires the configured Ollama models:

```bash
cd api
python scripts/seed_retrieval_baseline.py
RUN_RAG_INTEGRATION=1 python scripts/evaluate_retrieval.py \
  --dataset tests/fixtures/retrieval_cases_real.json \
  --top-k 5
```

See [Retrieval baseline](docs/retrieval-baseline.md) for the recorded results and index rebuild note.

## Main API paths

| Purpose | Method and path |
| --- | --- |
| Health | `GET /health` |
| Ready ingest formats | `GET /api/v1/articles/supported-formats` |
| Upload and ingest | `POST /api/v1/articles/upload` |
| Extracted document image | `GET /api/v1/articles/{document_id}/assets/{asset_path}` |
| Articles | `GET/POST /api/articles` |
| Article detail | `GET/PUT/DELETE /api/articles/{article_id}` |
| Semantic search | `POST /api/search` |
| RAG question | `POST /api/qa/ask` |
| Statistics | `GET /api/stats` |

## Important index migration

Embeddings are L2-normalized. Rebuild any ChromaDB index created before this behavior was introduced. Do not mix older raw vectors with normalized vectors in the same collection.
