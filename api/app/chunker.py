"""
Backward-compatible re-exports. Prefer ``app.services.chunking``.
"""

from app.services.chunking import (
    ChunkConfig,
    approximate_token_count,
    chunk_excel,
    chunk_markdown,
    recursive_split,
)

__all__ = [
    "ChunkConfig",
    "approximate_token_count",
    "chunk_excel",
    "chunk_markdown",
    "recursive_split",
]
