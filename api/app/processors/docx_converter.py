from pathlib import Path

import mammoth

from .converter_registry import register


@register(".docx")
def docx_to_markdown(file_path: str | Path) -> str:
    """
    Chuyển file DOCX sang Markdown.

    Hỗ trợ:
    - Heading
    - Paragraph
    - List
    - Table (mức cơ bản)

    Args:
        file_path: Đường dẫn tới file .docx

    Returns:
        Nội dung Markdown dạng string
    """

    path = Path(file_path)

    # Kiểm tra định dạng file
    if path.suffix.lower() != ".docx":
        raise ValueError(f"Không phải file DOCX: {path}")

    if not path.exists():
        raise FileNotFoundError(f"Không tìm thấy file: {path}")

    # Đọc DOCX và convert sang Markdown
    with path.open("rb") as docx_file:
        result = mammoth.convert_to_markdown(docx_file)

    markdown = result.value.strip()

    # Nếu không lấy được nội dung
    if not markdown:
        return (
            f"# {path.stem}\n\n"
            "_File trống hoặc không trích xuất được nội dung._\n"
        )

    return f"# {path.stem}\n\n{markdown}\n"