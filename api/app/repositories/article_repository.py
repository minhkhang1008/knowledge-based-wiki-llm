"""
Temporary in-memory implementation.

Task Hào Việt   
Không thay đổi tên hàm, thứ tự tham số và ý nghĩa giá trị trả về.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4
from app.models.article import Article
from sqlalchemy.ext.asyncio import AsyncSession 
from sqlalchemy import select, update, delete
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.exc import IntegrityError

class DuplicateDocumentError(Exception):
    """Raised when creating an Article with an existing document_id."""


def _to_dict(data: Any) -> dict[str, Any]:
    if isinstance(data, Mapping):
        return dict(data)

    if hasattr(data, "model_dump"):
        return data.model_dump(exclude_unset=True)

    raise TypeError("Article data must be a mapping or a Pydantic model")


async def get_article_by_id(
    session: AsyncSession,
    article_id: str,
) -> Article | None:
    try:
        stmt = select(Article).where(Article.id == article_id)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()
    except Exception: 
        await session.rollback()
        raise
    
    
async def get_article_by_document_id(
    session: AsyncSession,
    document_id: str,
) -> Article | None:
    try: 
        stmt = select(Article).where(Article.document_id == document_id)
        result = await session.execute(stmt)
        return  result.scalar_one_or_none()
    except Exception: 
        await session.rollback()
        raise


async def list_articles(
    session: AsyncSession,
    skip: int = 0,
    limit: int = 20,
    search: str | None = None,
) -> list[Article]:
    try: 
        stmt = select(Article).offset(skip).limit(limit)
        if search is not None:
            stmt = stmt.where(Article.title.like(f"%{search}%"))
        result = await session.execute(stmt)
        return list(result.scalars().all())
    except Exception: 
        await session.rollback()
        raise
    
    
async def create_article(
    session: AsyncSession,
    data: Any,
) -> Article:
    payload = _to_dict(data) 
    document_id = str(payload["document_id"])
    now = datetime.now(timezone.utc)
    try: 
        stmt = insert(Article).values(
            id=str(uuid4()),
            document_id=document_id,
            title=str(payload["title"]),
            content=str(payload["content"]),
            source_file=str(payload["source_file"]),
            created_at=now,
            updated_at=now,
        ).returning(Article)
        article = await session.execute(stmt)
        await session.commit()
        return article.scalar_one()
    except IntegrityError:
        await session.rollback()
        raise DuplicateDocumentError(f"document with ID: {document_id} is already exist")
    except Exception: 
        await session.rollback()
        raise  


async def update_article(
    session: AsyncSession,
    article_id: str,
    data: Any,
) -> Article | None:
    try:
        payload = _to_dict(data)
        stmt = update(Article).where(Article.id == article_id).values(
            title= payload.get("title", Article.title),
            content= payload.get("content", Article.content),
            source_file= payload.get("source_file", Article.source_file),
            updated_at= datetime.now(timezone.utc),
        ).returning(Article)
        result = await session.execute(stmt)
        await session.commit()
        return result.scalar_one_or_none()
    except Exception:
        await session.rollback()
        raise


async def delete_article(
    session: AsyncSession,
    article_id: str,
) -> bool:
    try: 
        stmt = delete(Article).where(Article.id == article_id).returning(Article.id)
        result = await session.execute(stmt)
        if result.scalar_one_or_none() is None:
            return False
        await session.commit()
        return True
    except Exception:
        await session.rollback()
        raise 


async def upsert_article_by_document_id(
    session: AsyncSession,
    data: Any,
) -> Article | None:
    payload = _to_dict(data)
    document_id = str(payload["document_id"])
    now = datetime.now(timezone.utc)
    try:
        stmt = insert(Article).values(
            id=str(uuid4()),
            document_id=document_id,
            title=str(payload["title"]),
            content=str(payload["content"]),
            source_file=str(payload["source_file"]),
            created_at=now,
            updated_at=now,
        )
        upsert_stmt = stmt.on_conflict_do_update(
            index_elements=['document_id'],
            set_={
                Article.title: stmt.excluded.title,             
                Article.content: stmt.excluded.content,           
                Article.source_file: stmt.excluded.source_file,
                Article.updated_at: now,
            }
        ).returning(Article)
        await session.execute(upsert_stmt)
        await session.commit()
    except Exception:
        await session.rollback()
        raise