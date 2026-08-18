import asyncio
import hashlib
import json
import os
from pathlib import Path
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.ollama_client import OLLAMA_EMBED_MODEL, generate_embeddings
from app.repositories.article_repository import (
    create_article,
    delete_article,
    get_article_by_id,
    update_article,
    upsert_article_by_document_id,
)
from app.services.services_vector_db import collection
from app.services.chunking import chunk_from_markdown
from app.services.chunking.chunker_registry import registered_extensions
from app.services.chunking.recursive import recursive_split
from app.services.vector_index_maintenance import delete_chunks_by_article_id


CHUNK_PARSER_VERSION = "structure-v2"
CHROMA_UPSERT_BATCH_SIZE = max(1, int(os.getenv("CHROMA_UPSERT_BATCH_SIZE", "64")))


def _chunk_article(article: Any) -> list[dict]:
    content = article.content.strip()
    source_file = str(article.source_file)
    source_ext = Path(source_file).suffix.lower()

    if source_ext in registered_extensions():
        return chunk_from_markdown(
            content,
            source=source_file,
            file_ext=source_ext,
        )

    return [
        {
            "content": chunk,
            "metadata": {"source_file": source_file},
        }
        for chunk in recursive_split(content)
    ]


def _build_chroma_metadata(article: Any, chunk: dict) -> dict:
    raw_metadata = chunk.get("metadata") or {}
    metadata = {
        key: value
        for key, value in raw_metadata.items()
        if value is not None and isinstance(value, (str, int, float, bool))
    }
    metadata.update({
        "article_id": str(article.id),
        "source_file": str(article.source_file),
        "parser_version": CHUNK_PARSER_VERSION,
    })
    return metadata


def _content_hash(article: Any, chunk: dict) -> str:
    metadata = chunk.get("metadata") or {}
    stable_metadata = {
        key: metadata.get(key)
        for key in ("page_number", "slide_number", "sheet", "row", "heading_path", "block_type")
        if metadata.get(key) is not None
    }
    payload = {
        "document_id": str(getattr(article, "document_id", article.id)),
        "content": " ".join(chunk["content"].split()),
        "metadata": stable_metadata,
        "parser_version": CHUNK_PARSER_VERSION,
        "embedding_model": OLLAMA_EMBED_MODEL,
    }
    return hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()


def _read_existing_chunks(article_id: str) -> tuple[dict[str, tuple[str, list[float]]], set[str]]:
    result = collection.get(
        where={"article_id": {"$eq": article_id}},
        include=["metadatas", "embeddings"],
    )
    ids = list(result.get("ids") or [])
    metadatas = list(result.get("metadatas") or [])
    raw_embeddings = result.get("embeddings")
    embeddings = list(raw_embeddings) if raw_embeddings is not None else []
    existing: dict[str, tuple[str, list[float]]] = {}
    for index, chunk_id in enumerate(ids):
        metadata = metadatas[index] if index < len(metadatas) and metadatas[index] else {}
        content_hash = metadata.get("content_hash")
        embedding = embeddings[index] if index < len(embeddings) else None
        if content_hash and embedding is not None:
            existing[str(content_hash)] = (
                str(chunk_id),
                [float(value) for value in embedding],
            )
    return existing, {str(chunk_id) for chunk_id in ids}


def _upsert_batches(
    ids: list[str],
    embeddings: list[list[float]],
    documents: list[str],
    metadatas: list[dict],
) -> None:
    for start in range(0, len(ids), CHROMA_UPSERT_BATCH_SIZE):
        end = start + CHROMA_UPSERT_BATCH_SIZE
        collection.upsert(
            ids=ids[start:end],
            embeddings=embeddings[start:end],
            documents=documents[start:end],
            metadatas=metadatas[start:end],
        )


async def index_article_to_chroma(article: Any) -> None:
    """Incrementally replace an article index without deleting good data first."""
    chunks = _chunk_article(article)
    if not chunks:
        if not str(article.content).strip():
            raise ValueError("Không thể index article rỗng.")
        # Ảnh/PDF không có text vẫn được lưu như asset nhưng không tạo vector rác.
        await asyncio.to_thread(delete_chunks_by_article_id, str(article.id))
        return

    article_id = str(article.id)
    existing, old_ids = await asyncio.to_thread(_read_existing_chunks, article_id)
    unique_chunks: list[dict] = []
    hashes: list[str] = []
    seen_hashes: set[str] = set()
    for chunk in chunks:
        content_hash = _content_hash(article, chunk)
        if content_hash in seen_hashes:
            continue
        seen_hashes.add(content_hash)
        unique_chunks.append(chunk)
        hashes.append(content_hash)
    chunks = unique_chunks
    missing_indexes = [index for index, value in enumerate(hashes) if value not in existing]
    new_embeddings = await generate_embeddings(
        [chunks[index]["content"] for index in missing_indexes]
    )
    generated = dict(zip(missing_indexes, new_embeddings))

    ids: list[str] = []
    embeddings: list[list[float]] = []
    metadatas: list[dict] = []
    for index, (chunk, content_hash) in enumerate(zip(chunks, hashes)):
        chunk_id = f"{article_id}:{content_hash[:32]}"
        ids.append(chunk_id)
        embeddings.append(
            existing[content_hash][1] if content_hash in existing else generated[index]
        )
        metadata = _build_chroma_metadata(article, chunk)
        metadata["content_hash"] = content_hash
        metadatas.append(metadata)

    await asyncio.to_thread(
        _upsert_batches,
        ids,
        embeddings,
        [chunk["content"] for chunk in chunks],
        metadatas,
    )
    stale_ids = sorted(old_ids - set(ids))
    if stale_ids:
        await asyncio.to_thread(collection.delete, ids=stale_ids)

async def create_article_lifecycle(
    session: AsyncSession,
    data: Any,
):
    article = await create_article(session, data)
    await index_article_to_chroma(article)
    return article


async def update_article_lifecycle(
    session: AsyncSession,
    article_id: str,
    data: Any,
):
    article = await update_article(session, article_id, data)
    if article is None:
        return None

    await index_article_to_chroma(article)
    return article


async def delete_article_lifecycle(
    session: AsyncSession,
    article_id: str,
) -> bool:
    article = await get_article_by_id(session, article_id)
    if article is None:
        return False

    await asyncio.to_thread(delete_chunks_by_article_id, article_id)
    return await delete_article(session, article_id)


async def upsert_article_lifecycle(
    session: AsyncSession,
    data: Any,
):
    article = await upsert_article_by_document_id(session, data)
    await index_article_to_chroma(article)
    return article
