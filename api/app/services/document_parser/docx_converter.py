from pathlib import Path
import mammoth
from app.services.document_parser.converter_registry import register

@register(".docx")
def docx_to_markdown(file_path: str | Path, output_dir: str) -> str:
    path = Path(file_path)

    if path.suffix.lower() != ".docx":
        raise ValueError(f"Không phải file DOCX: {path}")

    if not path.exists():
        raise FileNotFoundError(f"Không tìm thấy file: {path}")

    with path.open("rb") as docx_file:
        result = mammoth.convert_to_markdown(docx_file)

    markdown = result.value.strip()

    if not markdown:
        return f"# {path.stem}\n\n_File trống hoặc không trích xuất được nội dung._\n"

    return f"# {path.stem}\n\n{markdown}\n"