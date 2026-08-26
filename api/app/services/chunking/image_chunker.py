"""Chunk OCR-derived Markdown for standalone images."""

from __future__ import annotations

from pathlib import Path

from app.services.chunking.chunker_registry import register
from app.services.chunking.config import ChunkConfig
from app.services.chunking.structure import pack_semantic_units, parse_markdown_units


IMAGE_EXTENSIONS = (".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".tif", ".webp", ".gif")


def chunk_image(
    markdown_text: str,
    source: str,
    config: ChunkConfig | None = None,
) -> list[dict]:
    config = config or ChunkConfig()
    chunks = pack_semantic_units(parse_markdown_units(markdown_text), config)
    output: list[dict] = []
    for index, chunk in enumerate(chunks, start=1):
        metadata = dict(chunk.get("metadata") or {})
        metadata.update({
            "source_file": source,
            "chunk_id": str(index),
            "chunk_part": index,
            "image_number": 1,
            "source_extension": Path(source).suffix.lower(),
        })
        output.append({"content": chunk["content"], "metadata": metadata})
    return output


def _registered_image_chunker(
    markdown_text: str,
    source: str,
    config: ChunkConfig | None = None,
) -> list[dict]:
    return chunk_image(markdown_text, source, config)


for _extension in IMAGE_EXTENSIONS:
    register(_extension)(_registered_image_chunker)
