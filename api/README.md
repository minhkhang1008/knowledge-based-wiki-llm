# API

FastAPI backend for the Knowledge Based Wiki LLM project.

## Configuration

Copy `.env.example` to `.env`. Important values:

- `DATABASE_URL`: async SQLAlchemy connection string.
- `SQL_ECHO`: enables verbose SQL logging for local debugging.
- `CHROMA_PERSIST_PATH`: persistent ChromaDB directory.
- `EXTRACTED_DATA_DIR`: converted Markdown and extracted assets.
- `OLLAMA_HOST`: Ollama server origin.
- `OLLAMA_EMBED_MODEL`: embedding model.
- `OLLAMA_CHAT_MODEL`: chat model.
- `RAG_DISTANCE_THRESHOLD`: maximum accepted Chroma distance.
- `MAX_UPLOAD_SIZE_MB`: streamed upload limit.
- `CORS_ORIGINS`: comma-separated frontend origins.
- `ENABLE_LEGACY_OFFICE_FORMATS`: enables DOC, XLS, and PPT only when LibreOffice is installed.

## Ingest extension point

`GET /api/v1/articles/supported-formats` only returns extensions with both:

1. A converter registered under `app/services/document_parser`.
2. A chunker registered under `app/services/chunking`.

To add PDF or image ingest, register the corresponding chunker extension. The shared upload endpoint will then advertise and route that format automatically.

## Data consistency

Upload processing completes conversion, chunking, and embedding before changing the stored article. If vector replacement fails after the SQLite upsert, the service restores the previous article and Chroma snapshot, or removes the newly created article.

## Development

```bash
python -m venv ../.venv
source ../.venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env
uvicorn app.main:app --reload
```

```bash
python -m pytest -q
python -m compileall -q app scripts tests
```
