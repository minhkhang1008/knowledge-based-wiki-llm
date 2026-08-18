# Knowledge Based Wiki LLM

A local-first knowledge base that converts office documents to Markdown, chunks and embeds their content, stores searchable vectors in ChromaDB, and answers questions through Ollama with source citations.

## Current status

The backend supports:

- Article lifecycle in SQLite with ChromaDB synchronization.
- Semantic search with a calibrated distance threshold.
- RAG answers with required source citations and no-context handling.
- Document conversion and format-aware chunking for DOCX, XLSX, XLSM, and PPTX.
- One upload-to-index ingest endpoint with compensating rollback.
- Retrieval evaluation, index-integrity checks, and API tests.

PDF and image converters exist, but their chunkers are still pending. They are intentionally not advertised by the ingest API until both conversion and chunking are ready.

Frontend implementation is not part of the repository yet. See [Frontend requirements and integration guide](docs/frontend-integration.md).

## Quick start

Requirements:

- Python 3.11
- Ollama
- `nomic-embed-text`
- `llama3.2`

```bash
ollama pull nomic-embed-text
ollama pull llama3.2
python -m venv .venv
source .venv/bin/activate
pip install -r api/requirements-dev.txt
cp api/.env.example api/.env
cd api
uvicorn app.main:app --reload
```

Open `http://localhost:8000/docs` for the interactive API documentation.

## Docker Compose

The root Compose stack starts Ollama, downloads the configured embedding and chat models, starts the API, and persists both model and knowledge-base data:

```bash
cp .env.example .env
docker compose up --build
```

The first start takes longer because Ollama downloads both models. Verify readiness with:

```bash
curl http://localhost:8000/health
```

## Run tests

```bash
cd api
python -m pytest -q
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
| Articles | `GET/POST /api/articles` |
| Article detail | `GET/PUT/DELETE /api/articles/{article_id}` |
| Semantic search | `POST /api/search` |
| RAG question | `POST /api/qa/ask` |
| Statistics | `GET /api/stats` |

## Important index migration

Embeddings are L2-normalized. Rebuild any ChromaDB index created before this behavior was introduced. Do not mix older raw vectors with normalized vectors in the same collection.
