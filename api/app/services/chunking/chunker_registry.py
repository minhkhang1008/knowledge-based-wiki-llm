from typing import Callable

from .config import ChunkConfig

Chunker = Callable[[str, str, ChunkConfig | None], list[dict]]

REGISTRY: dict[str, Chunker] = {}


def register(ext: str):
    """Decorator đăng ký chunker cho một phần mở rộng file (vd. .docx, .xlsx)."""

    def decorator(func: Chunker):
        REGISTRY[ext.lower()] = func
        return func

    return decorator


def get_chunker(ext: str) -> Chunker | None:
    normalized = ext.lower()
    if not normalized.startswith("."):
        normalized = f".{normalized}"
    return REGISTRY.get(normalized)


def registered_extensions() -> list[str]:
    return sorted(REGISTRY.keys())
