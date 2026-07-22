"""
Shared OCR utility — tránh duplicate logic giữa image_converter và image_extractor.
"""
import logging
from collections import defaultdict

logger = logging.getLogger("ocr.utils")


def ocr_image_to_text(pil_image) -> str:
    """
    Chạy OCR trên PIL Image, trả về text đã gom dòng.
    Trả về "" nếu không có engine hoặc không nhận dạng được gì.
    """
    try:
        from app.services.ocr.factory import OCRFactory
        engine = OCRFactory.get_engine()
        words = engine.extract_words(pil_image, scale=1.0)
        if not words:
            return ""

        line_map: dict = defaultdict(list)
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
        logger.debug("OCR engine không khả dụng")
        return ""
    except Exception as e:
        logger.warning(f"OCR lỗi: {e}")
        return ""


def ocr_image_file_to_text(image_path: str) -> str:
    """Chạy OCR trên file ảnh."""
    try:
        from PIL import Image as PILImage
        pil_img = PILImage.open(image_path).convert("RGB")
        return ocr_image_to_text(pil_img)
    except Exception as e:
        logger.warning(f"Không thể mở ảnh {image_path}: {e}")
        return ""
