import asyncio
from collections.abc import Mapping
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.ollama_client import generate_embedding
from app.repositories.article_repository import (
    create_article,
    delete_article,
    get_article_by_id,
    get_article_by_document_id,
    update_article,
    upsert_article_by_document_id,
)
from app.services.services_vector_db import collection
from app.services.chunking.recursive import recursive_split
from app.services.vector_index_maintenance import delete_chunks_by_article_id


def snapshot_article_chunks(article_id: str) -> dict[str, Any]:
    return collection.get(
        where={"article_id": {"$eq": article_id}},
        include=["documents", "metadatas", "embeddings"],
    )


def restore_article_chunks(article_id: str, snapshot: dict[str, Any]) -> None:
    delete_chunks_by_article_id(article_id)
    ids = snapshot.get("ids") or []
    if not ids:
        return

    embeddings = snapshot.get("embeddings")
    if embeddings is None:
        raise ValueError("Snapshot ChromaDB thiếu embedding để hoàn tác.")
    collection.upsert(
        ids=ids,
        documents=snapshot.get("documents") or [],
        metadatas=snapshot.get("metadatas") or [],
        embeddings=embeddings,
    )


def _clean_metadata(metadata: Mapping[str, Any]) -> dict[str, str | int | float | bool]:
    """Keep only scalar metadata values accepted by ChromaDB."""
    return {
        str(key): value
        for key, value in metadata.items()
        if isinstance(value, (str, int, float, bool))
    }


async def generate_chunk_embeddings(chunks: list[dict]) -> list[list[float]]:
    embeddings: list[list[float]] = []
    for chunk in chunks:
        content = str(chunk.get("content", "")).strip()
        if not content:
            raise ValueError("Chunk rỗng không thể được lập chỉ mục.")
        embedding = await generate_embedding(content)
        if not embedding:
            raise ValueError("Không thể tạo embedding cho chunk.")
        embeddings.append(embedding)
    return embeddings


async def replace_article_chunks(
    article: Any,
    chunks: list[dict],
    embeddings: list[list[float]] | None = None,
) -> None:
    """Replace all indexed chunks for an article while preserving rich metadata."""
    if not chunks:
        raise ValueError("Tài liệu không tạo được chunk nào.")

    prepared_embeddings = embeddings or await generate_chunk_embeddings(chunks)
    if len(prepared_embeddings) != len(chunks):
        raise ValueError("Số embedding không khớp số chunk.")

    article_id = str(article.id)
    ids = [f"{article_id}:{index}" for index in range(len(chunks))]
    documents = [str(chunk["content"]).strip() for chunk in chunks]
    metadatas = []
    for index, chunk in enumerate(chunks):
        chunk_metadata = _clean_metadata(chunk.get("metadata", {}))
        chunk_metadata.update(
            {
                "article_id": article_id,
                "document_id": str(article.document_id),
                "source_file": str(article.source_file),
                "chunk_index": index,
            }
        )
        metadatas.append(chunk_metadata)

    snapshot = await asyncio.to_thread(snapshot_article_chunks, article_id)
    try:
        await asyncio.to_thread(delete_chunks_by_article_id, article_id)
        await asyncio.to_thread(
            collection.upsert,
            ids=ids,
            embeddings=prepared_embeddings,
            documents=documents,
            metadatas=metadatas,
        )
    except Exception:
        await asyncio.to_thread(restore_article_chunks, article_id, snapshot)
        raise


async def index_article_to_chroma(article: Any) -> None:
    """Replace an article's searchable vector entry after it changes."""
    content = article.content.strip()
    chunks = recursive_split(content)
    prepared_chunks = [
        {
            "content": chunk,
            "metadata": {"source_file": article.source_file},
        }
        for chunk in chunks
    ]
    await replace_article_chunks(article, prepared_chunks)

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
