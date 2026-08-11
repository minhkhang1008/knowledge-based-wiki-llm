from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.article_repository import create_article, delete_article, update_article, upsert_article_by_document_id
from app.services.vector_index_maintenance import delete_chunks_by_article_id

async def create_article_lifecycle(
    session: AsyncSession,
    data: Any,
):
    return await create_article(session, data)


async def update_article_lifecycle(
    session: AsyncSession,
    article_id: str,
    data: Any,
):
    article = await update_article(session, article_id, data)
    if article is None:
        return None

    delete_chunks_by_article_id(article_id)
    return article


async def delete_article_lifecycle(
    session: AsyncSession,
    article_id: str,
) -> bool:
    deleted = await delete_article(session, article_id)
    if not deleted:
        return False
    delete_chunks_by_article_id(article_id)
    return True


async def upsert_article_lifecycle(
    session: AsyncSession,
    data: Any,
):
    article = await upsert_article_by_document_id(session, data)
    delete_chunks_by_article_id(str(article.id))
    return article

