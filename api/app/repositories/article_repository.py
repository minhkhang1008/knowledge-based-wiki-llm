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


class DuplicateDocumentError(Exception):
    """Raised when creating an Article with an existing document_id."""


@dataclass(slots=True)
class ArticleRecord:
    id: str
    document_id: str
    title: str
    content: str
    source_file: str
    created_at: datetime
    updated_at: datetime


_ARTICLES: dict[str, ArticleRecord] = {}


def _to_dict(data: Any) -> dict[str, Any]:
    if isinstance(data, Mapping):
        return dict(data)

    if hasattr(data, "model_dump"):
        return data.model_dump(exclude_unset=True)

    raise TypeError("Article data must be a mapping or a Pydantic model")


async def get_article_by_id(
    session: Any,
    article_id: str,
) -> ArticleRecord | None:
    return _ARTICLES.get(article_id)


async def get_article_by_document_id(
    session: Any,
    document_id: str,
) -> ArticleRecord | None:
    for article in _ARTICLES.values():
        if article.document_id == document_id:
            return article

    return None


async def list_articles(
    session: Any,
    skip: int = 0,
    limit: int = 20,
    search: str | None = None,
) -> list[ArticleRecord]:
    articles = list(_ARTICLES.values())

    if search:
        keyword = search.casefold()
        articles = [
            article
            for article in articles
            if keyword in article.title.casefold()
        ]

    safe_skip = max(skip, 0)
    safe_limit = min(max(limit, 1), 100)

    return articles[safe_skip : safe_skip + safe_limit]


async def create_article(
    session: Any,
    data: Any,
) -> ArticleRecord:
    payload = _to_dict(data)
    document_id = str(payload["document_id"])

    existing = await get_article_by_document_id(session, document_id)
    if existing is not None:
        raise DuplicateDocumentError(
            f"document_id '{document_id}' already exists"
        )

    now = datetime.now(timezone.utc)

    article = ArticleRecord(
        id=str(uuid4()),
        document_id=document_id,
        title=str(payload["title"]),
        content=str(payload["content"]),
        source_file=str(payload["source_file"]),
        created_at=now,
        updated_at=now,
    )

    _ARTICLES[article.id] = article
    return article


async def update_article(
    session: Any,
    article_id: str,
    data: Any,
) -> ArticleRecord | None:
    article = await get_article_by_id(session, article_id)
    if article is None:
        return None

    payload = _to_dict(data)

    updated_article = replace(
        article,
        title=payload.get("title", article.title),
        content=payload.get("content", article.content),
        source_file=payload.get("source_file", article.source_file),
        updated_at=datetime.now(timezone.utc),
    )

    _ARTICLES[article_id] = updated_article
    return updated_article


async def delete_article(
    session: Any,
    article_id: str,
) -> bool:
    return _ARTICLES.pop(article_id, None) is not None


async def upsert_article_by_document_id(
    session: Any,
    data: Any,
) -> ArticleRecord:
    payload = _to_dict(data)
    document_id = str(payload["document_id"])

    existing = await get_article_by_document_id(session, document_id)

    if existing is None:
        return await create_article(session, payload)

    updated_article = replace(
        existing,
        title=str(payload["title"]),
        content=str(payload["content"]),
        source_file=str(payload["source_file"]),
        updated_at=datetime.now(timezone.utc),
    )

    _ARTICLES[existing.id] = updated_article
    return updated_article