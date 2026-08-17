"""Chunking for Word (.docx / .doc) after conversion to Markdown."""

from __future__ import annotations

import re
from typing import Iterator

from app.services.chunking.chunker_registry import register
from app.services.chunking.config import ChunkConfig
from app.services.chunking.recursive import approximate_token_count, recursive_split

HEADING_PATTERN = re.compile(r"^(#{1,3})\s+(.+)$")


def _split_by_headings(text: str) -> list[tuple[str, str]]:
    sections: list[tuple[str, str]] = []
    current_heading = ""
    current_lines: list[str] = []

    for line in text.splitlines(keepends=True):
        match = HEADING_PATTERN.match(line.rstrip("\n"))
        if match:
            if current_lines:
                sections.append((current_heading, "".join(current_lines)))
            current_heading = match.group(2).strip()
            current_lines = []
        else:
            current_lines.append(line)

    if current_lines:
        sections.append((current_heading, "".join(current_lines)))

    if not sections and text.strip():
        sections.append(("", text))

    return sections


def _iter_section_chunks(section_text: str, config: ChunkConfig) -> Iterator[str]:
    content = section_text.strip()
    if not content:
        return

    if approximate_token_count(content) <= config.chunk_size:
        yield content
        return

    yield from recursive_split(content, config.chunk_size, config.overlap)


def chunk_markdown(
    text: str,
    source: str,
    config: ChunkConfig | None = None,
) -> list[dict]:
    """
    Split Markdown into semantic chunks with metadata for RAG indexing.

    Returns a list of {"content": str, "metadata": dict} items.
    """
    config = config or ChunkConfig()
    sections = _split_by_headings(text)
    chunks: list[dict] = []
    chunk_id = 0

    for section_heading, section_content in sections:
        for content in _iter_section_chunks(section_content, config):
            chunk_id += 1
            chunks.append(
                {
                    "content": content,
                    "metadata": {
                        "source_file": source,
                        "section": section_heading,
                        "chunk_id": str(chunk_id),
                    },
                }
            )

    return chunks


@register(".docx")
@register(".doc")
def chunk_docx(
    markdown_text: str,
    source: str,
    config: ChunkConfig | None = None,
) -> list[dict]:
    return chunk_markdown(markdown_text, source, config)
