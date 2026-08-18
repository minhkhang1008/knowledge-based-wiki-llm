from __future__ import annotations

import asyncio
from collections.abc import Mapping
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
    get_article_by_document_id,
    get_article_by_id,
    update_article,
    upsert_article_by_document_id,
)
from app.services.chunking import chunk_from_markdown
from app.services.chunking.chunker_registry import registered_extensions
from app.services.chunking.recursive import recursive_split
from app.services.services_vector_db import collection
from app.services.vector_index_maintenance import delete_chunks_by_article_id


CHUNK_PARSER_VERSION = "structure-v2"
CHROMA_UPSERT_BATCH_SIZE = max(
    1,
    int(os.getenv("CHROMA_UPSERT_BATCH_SIZE", "64")),
)


def _chunk_article(article: Any) -> list[dict]:
    content = str(article.content).strip()
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


def _clean_metadata(
    metadata: Mapping[str, Any],
) -> dict[str, str | int | float | bool]:
    """Keep only scalar metadata values accepted by ChromaDB."""
    return {
        str(key): value
        for key, value in metadata.items()
        if value is not None and isinstance(value, (str, int, float, bool))
    }


def _build_chroma_metadata(
    article: Any,
    chunk: dict,
    chunk_index: int,
) -> dict[str, str | int | float | bool]:
    raw_metadata = chunk.get("metadata") or {}
    metadata = _clean_metadata(raw_metadata)
    metadata.update({
        "article_id": str(article.id),
        "document_id": str(article.document_id),
        "source_file": str(article.source_file),
        "chunk_index": chunk_index,
        "parser_version": CHUNK_PARSER_VERSION,
    })
    return metadata


def _content_hash(article: Any, chunk: dict) -> str:
    metadata = chunk.get("metadata") or {}
    stable_metadata = {
        key: metadata.get(key)
        for key in (
            "page_number",
            "slide_number",
            "sheet",
            "row",
            "heading_path",
            "block_type",
        )
        if metadata.get(key) is not None
    }
    payload = {
        "document_id": str(getattr(article, "document_id", article.id)),
        "content": " ".join(str(chunk["content"]).split()),
        "metadata": stable_metadata,
        "parser_version": CHUNK_PARSER_VERSION,
        "embedding_model": OLLAMA_EMBED_MODEL,
    }
    return hashlib.sha256(
        json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
        ).encode("utf-8")
    ).hexdigest()


def snapshot_article_chunks(article_id: str) -> dict[str, Any]:
    return collection.get(
        where={"article_id": {"$eq": article_id}},
        include=["documents", "metadatas", "embeddings"],
    )


def restore_article_chunks(article_id: str, snapshot: dict[str, Any]) -> None:
    """Restore the exact prior Chroma state after a partial write fails."""
    delete_chunks_by_article_id(article_id)
    ids = list(snapshot.get("ids") or [])
    if not ids:
        return

    raw_embeddings = snapshot.get("embeddings")
    if raw_embeddings is None:
        raise ValueError("Snapshot ChromaDB thiếu embedding để hoàn tác.")
    collection.upsert(
        ids=ids,
        documents=list(snapshot.get("documents") or []),
        metadatas=list(snapshot.get("metadatas") or []),
        embeddings=list(raw_embeddings),
    )


def _existing_embeddings(
    snapshot: dict[str, Any],
) -> tuple[dict[str, list[float]], set[str]]:
    ids = list(snapshot.get("ids") or [])
    metadatas = list(snapshot.get("metadatas") or [])
    raw_embeddings = snapshot.get("embeddings")
    embeddings = list(raw_embeddings) if raw_embeddings is not None else []
    existing: dict[str, list[float]] = {}

    for index, chunk_id in enumerate(ids):
        metadata = (
            metadatas[index]
            if index < len(metadatas) and metadatas[index]
            else {}
        )
        content_hash = metadata.get("content_hash")
        embedding = embeddings[index] if index < len(embeddings) else None
        if content_hash and embedding is not None:
            existing[str(content_hash)] = [float(value) for value in embedding]

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


async def generate_chunk_embeddings(chunks: list[dict]) -> list[list[float]]:
    contents = [str(chunk.get("content", "")).strip() for chunk in chunks]
    if not contents or any(not content for content in contents):
        raise ValueError("Chunk rỗng không thể được lập chỉ mục.")
    embeddings = await generate_embeddings(contents)
    if len(embeddings) != len(chunks):
        raise ValueError("Số embedding không khớp số chunk.")
    return embeddings


async def replace_article_chunks(
    article: Any,
    chunks: list[dict],
    embeddings: list[list[float]] | None = None,
) -> None:
    """Incrementally replace chunks and restore the snapshot on partial failure."""
    if not chunks:
        raise ValueError("Tài liệu không tạo được chunk nào.")
    if embeddings is not None and len(embeddings) != len(chunks):
        raise ValueError("Số embedding không khớp số chunk.")

    unique_chunks: list[dict] = []
    hashes: list[str] = []
    supplied_embeddings: list[list[float]] = []
    seen_hashes: set[str] = set()
    for index, chunk in enumerate(chunks):
        content = str(chunk.get("content", "")).strip()
        if not content:
            raise ValueError("Chunk rỗng không thể được lập chỉ mục.")
        content_hash = _content_hash(article, chunk)
        if content_hash in seen_hashes:
            continue
        seen_hashes.add(content_hash)
        unique_chunks.append(chunk)
        hashes.append(content_hash)
        if embeddings is not None:
            supplied_embeddings.append(embeddings[index])

    article_id = str(article.id)
    snapshot = await asyncio.to_thread(snapshot_article_chunks, article_id)
    existing, old_ids = _existing_embeddings(snapshot)

    if embeddings is None:
        missing_indexes = [
            index
            for index, content_hash in enumerate(hashes)
            if content_hash not in existing
        ]
        generated_embeddings = await generate_embeddings([
            str(unique_chunks[index]["content"]).strip()
            for index in missing_indexes
        ])
        generated = dict(zip(missing_indexes, generated_embeddings))
        prepared_embeddings = [
            existing[content_hash]
            if content_hash in existing
            else generated[index]
            for index, content_hash in enumerate(hashes)
        ]
    else:
        prepared_embeddings = supplied_embeddings

    ids = [f"{article_id}:{content_hash[:32]}" for content_hash in hashes]
    documents = [str(chunk["content"]).strip() for chunk in unique_chunks]
    metadatas: list[dict] = []
    for index, (chunk, content_hash) in enumerate(zip(unique_chunks, hashes)):
        metadata = _build_chroma_metadata(article, chunk, index)
        metadata["content_hash"] = content_hash
        metadatas.append(metadata)

    try:
        await asyncio.to_thread(
            _upsert_batches,
            ids,
            prepared_embeddings,
            documents,
            metadatas,
        )
        stale_ids = sorted(old_ids - set(ids))
        if stale_ids:
            await asyncio.to_thread(collection.delete, ids=stale_ids)
    except Exception:
        await asyncio.to_thread(
            restore_article_chunks,
            article_id,
            snapshot,
        )
        raise


async def index_article_to_chroma(article: Any) -> None:
    chunks = _chunk_article(article)
    if not chunks:
        if not str(article.content).strip():
            raise ValueError("Không thể index article rỗng.")
        # Asset không có OCR/caption được lưu ở SQLite nhưng không tạo vector rác.
        await asyncio.to_thread(delete_chunks_by_article_id, str(article.id))
        return
    await replace_article_chunks(article, chunks)


async def create_article_lifecycle(
    session: AsyncSession,
    data: Any,
):
    article = await create_article(session, data)
    try:
        await index_article_to_chroma(article)
    except Exception:
        await delete_article(session, str(article.id))
        raise
    return article


async def update_article_lifecycle(
    session: AsyncSession,
    article_id: str,
    data: Any,
):
    previous = await get_article_by_id(session, article_id)
    if previous is None:
        return None
    previous_data = {
        "title": str(previous.title),
        "content": str(previous.content),
        "source_file": str(previous.source_file),
    }
    article = await update_article(session, article_id, data)
    if article is None:
        return None

    try:
        await index_article_to_chroma(article)
    except Exception:
        await update_article(session, article_id, previous_data)
        raise
    return article


async def delete_article_lifecycle(
    session: AsyncSession,
    article_id: str,
) -> bool:
    article = await get_article_by_id(session, article_id)
    if article is None:
        return False

    snapshot = await asyncio.to_thread(snapshot_article_chunks, article_id)
    await asyncio.to_thread(delete_chunks_by_article_id, article_id)
    try:
        deleted = await delete_article(session, article_id)
    except Exception:
        await asyncio.to_thread(restore_article_chunks, article_id, snapshot)
        raise
    if not deleted:
        await asyncio.to_thread(restore_article_chunks, article_id, snapshot)
    return deleted


async def upsert_article_lifecycle(
    session: AsyncSession,
    data: Any,
):
    payload = data.model_dump() if hasattr(data, "model_dump") else dict(data)
    previous = await get_article_by_document_id(
        session,
        str(payload["document_id"]),
    )
    previous_data = None
    if previous is not None:
        previous_data = {
            "title": str(previous.title),
            "content": str(previous.content),
            "source_file": str(previous.source_file),
        }

    article = await upsert_article_by_document_id(session, data)
    try:
        await index_article_to_chroma(article)
    except Exception:
        if previous_data is None:
            await delete_article(session, str(article.id))
        else:
            await update_article(session, str(article.id), previous_data)
        raise
    return article
