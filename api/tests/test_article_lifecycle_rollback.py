from __future__ import annotations

import asyncio
from types import SimpleNamespace

from app.services import article_lifecycle_service as lifecycle


def test_create_article_is_removed_when_indexing_fails(monkeypatch) -> None:
    article = SimpleNamespace(id="article-1")
    deleted: list[str] = []

    async def fake_create(*_):
        return article

    async def fake_index(*_):
        raise RuntimeError("index failed")

    async def fake_delete(_, article_id):
        deleted.append(article_id)
        return True

    monkeypatch.setattr(lifecycle, "create_article", fake_create)
    monkeypatch.setattr(lifecycle, "index_article_to_chroma", fake_index)
    monkeypatch.setattr(lifecycle, "delete_article", fake_delete)

    async def scenario() -> None:
        try:
            await lifecycle.create_article_lifecycle(object(), object())
        except RuntimeError as exc:
            assert str(exc) == "index failed"
        else:
            raise AssertionError("Expected indexing to fail")

    asyncio.run(scenario())
    assert deleted == ["article-1"]


def test_update_article_restores_previous_fields_when_indexing_fails(
    monkeypatch,
) -> None:
    previous = SimpleNamespace(
        id="article-1",
        title="Old title",
        content="Old content",
        source_file="old.docx",
    )
    updated = SimpleNamespace(id="article-1")
    updates: list[object] = []

    async def fake_get(*_):
        return previous

    async def fake_update(_, __, data):
        updates.append(data)
        return updated

    async def fake_index(*_):
        raise RuntimeError("index failed")

    monkeypatch.setattr(lifecycle, "get_article_by_id", fake_get)
    monkeypatch.setattr(lifecycle, "update_article", fake_update)
    monkeypatch.setattr(lifecycle, "index_article_to_chroma", fake_index)

    async def scenario() -> None:
        try:
            await lifecycle.update_article_lifecycle(
                object(),
                "article-1",
                {"title": "New title"},
            )
        except RuntimeError as exc:
            assert str(exc) == "index failed"
        else:
            raise AssertionError("Expected indexing to fail")

    asyncio.run(scenario())
    assert updates[-1] == {
        "title": "Old title",
        "content": "Old content",
        "source_file": "old.docx",
    }
