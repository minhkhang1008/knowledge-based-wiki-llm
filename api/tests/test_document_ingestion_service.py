from __future__ import annotations

import asyncio
from pathlib import Path

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.database import Base
from app.repositories.article_repository import get_article_by_document_id
from app.services import document_ingestion_service as ingestion


class FakeParser:
    def __init__(self, markdown_path: Path):
        self.markdown_path = markdown_path

    @staticmethod
    def calculate_sha256(_: str) -> str:
        return "real-document-hash"

    def process_file(self, _: str) -> str:
        return str(self.markdown_path)


async def _session_factory(tmp_path: Path):
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'test.db'}")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    return engine, async_sessionmaker(engine, expire_on_commit=False)


def test_ingest_document_creates_article_and_preserves_chunk_metadata(
    tmp_path,
    monkeypatch,
) -> None:
    source_path = tmp_path / "policy.docx"
    source_path.write_bytes(b"fake-office-file")
    markdown_path = tmp_path / "document.md"
    markdown_path.write_text(
        "# Chính sách\n\nNhân viên có 12 ngày phép năm.",
        encoding="utf-8",
    )
    captured: dict = {}

    async def fake_embeddings(chunks):
        return [[1.0, 0.0] for _ in chunks]

    async def fake_replace(article, chunks, embeddings):
        captured["article_id"] = article.id
        captured["chunks"] = chunks
        captured["embeddings"] = embeddings

    monkeypatch.setattr(ingestion, "generate_chunk_embeddings", fake_embeddings)
    monkeypatch.setattr(ingestion, "replace_article_chunks", fake_replace)

    async def scenario() -> None:
        engine, session_factory = await _session_factory(tmp_path)
        async with session_factory() as session:
            result = await ingestion.ingest_document(
                session,
                source_path,
                source_file="policy.docx",
                title="Chính sách nhân sự",
                parser=FakeParser(markdown_path),
            )
            stored = await get_article_by_document_id(session, "real-document-hash")

        await engine.dispose()
        assert stored is not None
        assert result.article.id == stored.id
        assert result.chunk_count == 1
        assert captured["article_id"] == stored.id
        assert captured["chunks"][0]["metadata"]["file_type"] == "docx"
        assert captured["embeddings"] == [[1.0, 0.0]]

    asyncio.run(scenario())


def test_ingest_document_rolls_back_new_article_when_vector_index_fails(
    tmp_path,
    monkeypatch,
) -> None:
    source_path = tmp_path / "policy.docx"
    source_path.write_bytes(b"fake-office-file")
    markdown_path = tmp_path / "document.md"
    markdown_path.write_text("# Chính sách\n\nNội dung.", encoding="utf-8")

    async def fake_embeddings(chunks):
        return [[1.0, 0.0] for _ in chunks]

    async def failing_replace(*_):
        raise RuntimeError("Chroma unavailable")

    monkeypatch.setattr(ingestion, "generate_chunk_embeddings", fake_embeddings)
    monkeypatch.setattr(ingestion, "replace_article_chunks", failing_replace)

    async def scenario() -> None:
        engine, session_factory = await _session_factory(tmp_path)
        async with session_factory() as session:
            try:
                await ingestion.ingest_document(
                    session,
                    source_path,
                    source_file="policy.docx",
                    parser=FakeParser(markdown_path),
                )
            except RuntimeError as exc:
                assert str(exc) == "Chroma unavailable"
            else:
                raise AssertionError("Expected vector indexing to fail")

            stored = await get_article_by_document_id(session, "real-document-hash")

        await engine.dispose()
        assert stored is None

    asyncio.run(scenario())
