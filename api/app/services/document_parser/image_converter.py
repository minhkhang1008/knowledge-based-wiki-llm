import os
import logging
from pathlib import Path
from app.services.document_parser.converter_registry import register

logger = logging.getLogger("image_converter")

# Tất cả định dạng ảnh phổ biến được hỗ trợ
_SUPPORTED_IMAGE_FORMATS = [
    ".png", ".jpg", ".jpeg", ".bmp",
    ".tiff", ".tif", ".webp", ".gif",
]


def _image_to_markdown(file_path: str | Path, output_dir: str) -> str:
    """
    Convert ảnh sang Markdown bằng OCR.
    - Nếu có OCR engine: extract text, trả về text + link ảnh
    - Nếu không có: chỉ trả về link ảnh (alt text)

    Output format:
        ![filename](images/filename.png)
        > text nhận dạng từ ảnh...
    """
    file_path = Path(file_path)
    os.makedirs(output_dir, exist_ok=True)

    # Copy ảnh vào output_dir/images/
    images_dir = os.path.join(output_dir, "images")
    os.makedirs(images_dir, exist_ok=True)
    dest_path = os.path.join(images_dir, file_path.name)
    if str(file_path.resolve()) != str(Path(dest_path).resolve()):
        import shutil
        shutil.copy2(str(file_path), dest_path)

    alt_text = file_path.stem  # tên file không có extension làm alt text
    markdown = f"![{alt_text}](images/{file_path.name})\n"

    # OCR
    ocr_text = _run_ocr(str(file_path))
    if ocr_text:
        markdown += f"\n> **Nội dung nhận dạng từ ảnh:**\n> {ocr_text}\n"

    return markdown


def _run_ocr(image_path: str) -> str:
    """Chạy OCR trên ảnh, trả về text hoặc "" nếu không có engine."""
    try:
        from PIL import Image as PILImage
        from app.services.ocr.factory import OCRFactory
        from collections import defaultdict

        engine = OCRFactory.get_engine()
        pil_img = PILImage.open(image_path).convert("RGB")
        logger.info(f"OCR [{engine.name}] → {os.path.basename(image_path)}")

        words = engine.extract_words(pil_img, scale=1.0)
        if not words:
            return ""

        # Gom words theo dòng (bucket theo y)
        line_map = defaultdict(list)
        for w in words:
            y_key = round(float(w.get("top", 0)) / 5) * 5
            line_map[y_key].append(w["text"])

        lines = [
            " ".join(line_map[y])
            for y in sorted(line_map.keys())
            if line_map[y]
        ]
        return "\n> ".join(lines)

    except ImportError:
        logger.debug("Không có OCR engine, bỏ qua OCR cho ảnh")
        return ""
    except Exception as e:
        logger.warning(f"OCR lỗi: {e}")
        return ""


# Đăng ký tất cả định dạng ảnh vào registry
for _ext in _SUPPORTED_IMAGE_FORMATS:
    register(_ext)(_image_to_markdown)
