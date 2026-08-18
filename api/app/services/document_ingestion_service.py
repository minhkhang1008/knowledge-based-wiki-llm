from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.article_repository import (
    delete_article,
    get_article_by_document_id,
    update_article,
    upsert_article_by_document_id,
)
from app.services.article_lifecycle_service import (
    generate_chunk_embeddings,
    replace_article_chunks,
)
from app.services.chunking.chunker_registry import get_chunker, registered_extensions
from app.services.chunking.pipeline import chunk_from_markdown
from app.services.document_parser.converter_registry import get_converter
from app.services.document_parser.pipeline import DocumentParserPipeline


LEGACY_TARGET_EXTENSIONS = {
    ".doc": ".docx",
    ".xls": ".xlsx",
    ".ppt": ".pptx",
}


@dataclass(frozen=True)
class IngestionResult:
    article: Any
    chunk_count: int
    document_id: str
    markdown_path: str


def normalized_chunk_extension(source_extension: str) -> str:
    extension = source_extension.lower()
    if not extension.startswith("."):
        extension = f".{extension}"
    return LEGACY_TARGET_EXTENSIONS.get(extension, extension)


def supported_ingestion_extensions() -> list[str]:
    """Return formats with both a converter path and a registered chunker."""
    ready: set[str] = set()
    for extension in registered_extensions():
        if get_converter(extension) is not None:
            ready.add(extension)

    if os.getenv("ENABLE_LEGACY_OFFICE_FORMATS", "false").lower() == "true":
        for legacy_extension, target_extension in LEGACY_TARGET_EXTENSIONS.items():
            if get_chunker(target_extension) is not None:
                ready.add(legacy_extension)

    return sorted(ready)


async def _restore_article(
    session: AsyncSession,
    article_id: str,
    previous_article: dict[str, str] | None,
) -> None:
    if previous_article is None:
        await delete_article(session, article_id)
        return

    await update_article(
        session,
        article_id,
        {
            "title": previous_article["title"],
            "content": previous_article["content"],
            "source_file": previous_article["source_file"],
        },
    )


async def ingest_document(
    session: AsyncSession,
    file_path: str | Path,
    source_file: str,
    title: str | None = None,
    parser: DocumentParserPipeline | None = None,
) -> IngestionResult:
    path = Path(file_path)
    source_extension = path.suffix.lower()
    chunk_extension = normalized_chunk_extension(source_extension)
    supported = supported_ingestion_extensions()

    if source_extension not in supported:
        supported_text = ", ".join(supported) or "chưa có"
        raise ValueError(
            f"Định dạng '{source_extension or '(không có)'}' chưa sẵn sàng ingest. "
            f"Các định dạng hiện có: {supported_text}."
        )

    active_parser = parser or DocumentParserPipeline()
    document_id = await asyncio.to_thread(active_parser.calculate_sha256, str(path))
    markdown_path = await asyncio.to_thread(active_parser.process_file, str(path))
    markdown_content = await asyncio.to_thread(
        Path(markdown_path).read_text,
        encoding="utf-8",
    )
    chunks = chunk_from_markdown(
        markdown_content,
        source_file,
        chunk_extension,
    )
    if not chunks:
        raise ValueError("Tài liệu không tạo được nội dung có thể tìm kiếm.")

    for chunk in chunks:
        chunk.setdefault("metadata", {})["file_type"] = source_extension.lstrip(".")

    embeddings = await generate_chunk_embeddings(chunks)
    previous = await get_article_by_document_id(session, document_id)
    previous_article = None
    if previous is not None:
        previous_article = {
            "title": str(previous.title),
            "content": str(previous.content),
            "source_file": str(previous.source_file),
        }

    article = await upsert_article_by_document_id(
        session,
        {
            "document_id": document_id,
            "title": (title or path.stem).strip() or path.stem,
            "content": markdown_content,
            "source_file": source_file,
        },
    )

    try:
        await replace_article_chunks(article, chunks, embeddings)
    except Exception:
        await _restore_article(
            session,
            str(article.id),
            previous_article,
        )
        raise

    return IngestionResult(
        article=article,
        chunk_count=len(chunks),
        document_id=document_id,
        markdown_path=str(markdown_path),
    )
