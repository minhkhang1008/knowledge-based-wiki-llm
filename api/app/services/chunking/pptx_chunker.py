"""Chunking for PowerPoint (.pptx) after conversion to Markdown."""

from __future__ import annotations

import re

from app.services.chunking.chunker_registry import register
from app.services.chunking.config import ChunkConfig
from app.services.chunking.recursive import (
    approximate_token_count,
    recursive_split,
)


FRONT_MATTER_PATTERN = re.compile(
    r"\A---\s*\r?\n.*?\r?\n---\s*(?:\r?\n|$)",
    re.DOTALL,
)
SLIDE_SEPARATOR_PATTERN = re.compile(r"(?m)^\s*---\s*$")
SLIDE_TITLE_PATTERN = re.compile(r"(?m)^##\s+(.+?)\s*$")


def _remove_front_matter(markdown_text: str) -> str:
    return FRONT_MATTER_PATTERN.sub("", markdown_text, count=1).strip()


def _split_slides(markdown_text: str) -> list[str]:
    content = _remove_front_matter(markdown_text)
    if not content:
        return []

    return [
        block.strip()
        for block in SLIDE_SEPARATOR_PATTERN.split(content)
        if block.strip()
    ]


def _extract_slide_title_and_body(slide_text: str) -> tuple[str, str]:
    match = SLIDE_TITLE_PATTERN.search(slide_text)
    if match is None:
        return "[Untitled Slide]", slide_text.strip()

    title = match.group(1).strip()
    body = (slide_text[: match.start()] + slide_text[match.end() :]).strip()
    return title, body


def _split_slide_content(
    title: str,
    body: str,
    config: ChunkConfig,
) -> list[str]:
    title_prefix = f"## {title}"
    if not body:
        return [title_prefix]

    complete_slide = f"{title_prefix}\n\n{body}"
    if approximate_token_count(complete_slide) <= config.chunk_size:
        return [complete_slide]

    title_tokens = approximate_token_count(title_prefix)
    body_chunk_size = max(50, config.chunk_size - title_tokens - 5)
    body_overlap = min(config.overlap, max(0, body_chunk_size // 3))
    body_parts = recursive_split(
        body,
        chunk_size=body_chunk_size,
        overlap=body_overlap,
    )

    return [
        f"{title_prefix}\n\n{part}".strip()
        for part in body_parts
        if part.strip()
    ]


def chunk_pptx(
    markdown_text: str,
    source: str,
    config: ChunkConfig | None = None,
) -> list[dict]:
    """Split converted PowerPoint Markdown without crossing slide boundaries."""
    config = config or ChunkConfig()
    slides = _split_slides(markdown_text)
    chunks: list[dict] = []
    chunk_id = 0

    for slide_number, slide_text in enumerate(slides, start=1):
        slide_title, slide_body = _extract_slide_title_and_body(slide_text)
        parts = _split_slide_content(slide_title, slide_body, config)

        for part_number, content in enumerate(parts, start=1):
            chunk_id += 1
            chunks.append(
                {
                    "content": content,
                    "metadata": {
                        "source_file": source,
                        "page_number": slide_number,
                        "slide_number": slide_number,
                        "slide_title": slide_title,
                        "chunk_id": str(chunk_id),
                        "chunk_part": part_number,
                    },
                }
            )

    return chunks


@register(".pptx")
def chunk_pptx_file(
    markdown_text: str,
    source: str,
    config: ChunkConfig | None = None,
) -> list[dict]:
    return chunk_pptx(markdown_text, source, config)
