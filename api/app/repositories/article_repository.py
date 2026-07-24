"""
Temporary in-memory implementation.

Task Hào Việt   
Không thay đổi tên hàm, thứ tự tham số và ý nghĩa giá trị trả về.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4
from app.models.article import Article
from sqlalchemy.ext.asyncio import AsyncSession 
from sqlalchemy import select, update, delete
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
    try: 
        now = datetime.now(timezone.utc)
        article = Article(
            id=str(uuid4()),
            document_id=document_id,
            title=str(payload["title"]),
            content=str(payload["content"]),
            source_file=str(payload["source_file"]),
            created_at=now,
            updated_at=now,
        )
        session.add(article)
        await session.flush()
        await session.commit()
        return article
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
        if result.scalar_one_or_none is None:
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
    existing = await get_article_by_document_id(session, document_id)
    if existing is None:
        return await create_article(session, payload)
    article_id = str(Article.id)
    return await update_article(session, article_id, payload) 