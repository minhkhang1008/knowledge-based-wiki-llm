from pathlib import Path

from app.services.chunking.chunker_registry import get_chunker, registered_extensions
from app.services.chunking.config import ChunkConfig


def chunk_from_markdown(
    markdown_text: str,
    source: str,
    file_ext: str,
    config: ChunkConfig | None = None,
) -> list[dict]:
    """
    Chọn chunker theo phần mở rộng file gốc (sau bước convert → Markdown).

    Word/Excel đăng ký trong ``docx_chunker`` / ``excel_chunker``.
    PDF, PPT, ảnh, … do thành viên khác thêm file + ``@register`` tương ứng.
    """
    ext = file_ext.lower()
    if not ext.startswith("."):
        ext = f".{ext}"

    chunker = get_chunker(ext)
    if chunker is None:
        supported = ", ".join(registered_extensions()) or "(chưa có)"
        raise ValueError(
            f"Chưa có chunker cho định dạng '{ext}'. "
            f"Các định dạng đã đăng ký: {supported}"
        )

    return chunker(markdown_text, source, config)


def chunk_markdown_file(
    md_path: str | Path,
    source_ext: str,
    source: str | None = None,
    config: ChunkConfig | None = None,
) -> list[dict]:
    path = Path(md_path)
    text = path.read_text(encoding="utf-8")
    return chunk_from_markdown(
        text,
        source or path.name,
        source_ext,
        config,
    )
