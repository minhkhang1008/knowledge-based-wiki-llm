"""Chunking for PDF Markdown while preserving source page numbers."""

from __future__ import annotations

import hashlib
import re

from app.services.chunking.chunker_registry import register
from app.services.chunking.config import ChunkConfig
from app.services.chunking.structure import parse_markdown_units, pack_semantic_units


PAGE_MARKER_PATTERN = re.compile(
    r"^\s*<!--\s*page:\s*(\d+)\s*-->\s*$",
    re.IGNORECASE,
)


def _split_pages(markdown_text: str) -> list[tuple[int | None, str]]:
    """Split Markdown on page markers emitted by ``MarkdownCompiler``."""
    pages: list[tuple[int | None, str]] = []
    current_page: int | None = None
    current_lines: list[str] = []

    def flush() -> None:
        content = "\n".join(current_lines).strip()
        if content:
            pages.append((current_page, content))

    for line in markdown_text.splitlines():
        marker = PAGE_MARKER_PATTERN.match(line)
        if marker:
            flush()
            current_lines = []
            current_page = int(marker.group(1))
            continue
        current_lines.append(line)

    flush()
    return pages


def chunk_pdf(
    markdown_text: str,
    source: str,
    config: ChunkConfig | None = None,
) -> list[dict]:
    """Split each PDF page independently and attach citation metadata."""
    config = config or ChunkConfig()
    chunks: list[dict] = []
    chunk_id = 0
    seen: set[tuple[int | None, str]] = set()

    for page_number, page_content in _split_pages(markdown_text):
        parts = pack_semantic_units(parse_markdown_units(page_content), config)
        page_part = 0
        for part in parts:
            content = part["content"]
            normalized = re.sub(r"\s+", " ", content).strip().casefold()
            dedup_key = (page_number, normalized)
            if not normalized or dedup_key in seen:
                continue
            seen.add(dedup_key)
            page_part += 1
            chunk_id += 1
            metadata: dict[str, str | int] = {
                "source_file": source,
                "chunk_id": str(chunk_id),
                "chunk_part": page_part,
            }
            metadata.update(part.get("metadata") or {})
            if page_number is not None:
                metadata["page_number"] = page_number
            heading_key = str(metadata.get("heading_path", ""))
            parent_key = hashlib.sha1(heading_key.casefold().encode("utf-8")).hexdigest()[:12]
            metadata["parent_id"] = f"page:{page_number or 0}:{parent_key[:80]}"
            metadata["child_index"] = page_part

            chunks.append({
                "content": content,
                "metadata": metadata,
            })

    return chunks


@register(".pdf")
def chunk_pdf_file(
    markdown_text: str,
    source: str,
    config: ChunkConfig | None = None,
) -> list[dict]:
    return chunk_pdf(markdown_text, source, config)
