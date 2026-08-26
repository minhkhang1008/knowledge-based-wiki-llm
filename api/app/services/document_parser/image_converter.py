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
    ocr_result = _run_ocr(str(file_path))
    if not ocr_result.text:
        from app.services.document_parser.vision_caption import generate_image_caption
        from app.services.ocr.ocr_utils import OCRResult

        caption, vision_model = generate_image_caption(file_path)
        if caption:
            ocr_result = OCRResult(
                text=f"Mô tả trực quan: {caption}",
                regions=[],
                engine=f"vision:{vision_model}",
                confidence=1.0,
            )
    if ocr_result.text:
        bbox = ""
        if ocr_result.regions:
            bbox = "; bbox=" + ",".join(f"{value:.1f}" for value in (
                min(region.bbox[0] for region in ocr_result.regions),
                min(region.bbox[1] for region in ocr_result.regions),
                max(region.bbox[2] for region in ocr_result.regions),
                max(region.bbox[3] for region in ocr_result.regions),
            ))
        markdown += (
            f"\n<!-- ocr-meta: engine={ocr_result.engine}; "
            f"confidence={ocr_result.confidence:.4f}; regions={len(ocr_result.regions)}{bbox} -->\n"
            "> **Nội dung nhận dạng từ ảnh:**\n> "
            + ocr_result.text.replace("\n", "\n> ")
            + "\n"
        )

    return markdown


def _run_ocr(image_path: str):
    """Chạy OCR trên ảnh và giữ confidence/region metadata."""
    from app.services.ocr.ocr_utils import ocr_image_file_to_result
    return ocr_image_file_to_result(image_path)


# Đăng ký tất cả định dạng ảnh vào registry
for _ext in _SUPPORTED_IMAGE_FORMATS:
    register(_ext)(_image_to_markdown)
