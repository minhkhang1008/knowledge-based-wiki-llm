import asyncio
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.ollama_client import generate_embedding
from app.repositories.article_repository import (
    create_article,
    delete_article,
    get_article_by_id,
    update_article,
    upsert_article_by_document_id,
)
from app.services.services_vector_db import collection
from app.services.vector_index_maintenance import delete_chunks_by_article_id


async def index_article_to_chroma(article: Any) -> None:
    """Replace an article's searchable vector entry after it changes."""
    content = article.content.strip()
    embedding = await generate_embedding(content)
    if not embedding:
        raise ValueError("Không thể tạo embedding cho article rỗng.")

    await asyncio.to_thread(
        collection.upsert,
        ids=[str(article.id)],
        embeddings=[embedding],
        documents=[content],
        metadatas=[
            {
                "article_id": str(article.id),
                "source_file": article.source_file,
            }
        ],
    )

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

    await asyncio.to_thread(delete_chunks_by_article_id, article_id)
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
    await asyncio.to_thread(delete_chunks_by_article_id, str(article.id))
    await index_article_to_chroma(article)
    return article
