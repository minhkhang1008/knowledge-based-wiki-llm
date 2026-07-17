import logging
import os
import shutil
from typing import List

from app.services.ocr.base import BaseOCREngine

logger = logging.getLogger("ocr.tesseract")

# Các vị trí thường gặp của Tesseract binary trên Windows
_WINDOWS_PATHS = [
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
    r"C:\Users\{username}\AppData\Local\Programs\Tesseract-OCR\tesseract.exe",
]


def _find_tesseract_binary() -> str | None:
    """Tự động tìm tesseract.exe trên Windows nếu chưa có trong PATH."""
    if shutil.which("tesseract"):
        return None  # đã có trong PATH, không cần set thủ công

    username = os.getenv("USERNAME", "")
    for p in _WINDOWS_PATHS:
        resolved = p.format(username=username)
        if os.path.exists(resolved):
            return resolved
    return None


class TesseractEngine(BaseOCREngine):
    """
    OCR engine dùng Tesseract — fallback engine (stub, chưa tối ưu).
    Yêu cầu cài Tesseract binary riêng:
      - Linux/Docker: apt-get install tesseract-ocr
      - Windows: tải installer từ https://github.com/UB-Mannheim/tesseract/wiki

    TODO (nếu chuyển sang Tesseract):
      - Tuning --psm (page segmentation mode)
      - Hỗ trợ tiếng Việt qua tessdata/vie.traineddata
      - Xử lý ảnh tiền xử lý (denoise, threshold) để tăng accuracy
    """

    def __init__(self, lang: str = "eng+vie"):
        self._lang = lang
        self._configured = False

    def _configure(self):
        """Set tesseract_cmd nếu cần, chỉ làm một lần."""
        if self._configured:
            return
        try:
            import pytesseract
            binary = _find_tesseract_binary()
            if binary:
                pytesseract.pytesseract.tesseract_cmd = binary
                logger.info(f"Tesseract binary tìm thấy tại: {binary}")
            self._configured = True
        except ImportError as e:
            raise ImportError(
                "pytesseract chưa được cài. Chạy: pip install pytesseract"
            ) from e

    @property
    def name(self) -> str:
        return "tesseract"

    def extract_words(self, pil_image, scale: float = 1.0) -> List[dict]:
        """
        Nhận dạng text từ PIL Image bằng Tesseract.
        Stub implementation — hoạt động nhưng chưa được tối ưu.
        """
        self._configure()

        try:
            import pytesseract
        except ImportError as e:
            raise ImportError("pytesseract chưa được cài.") from e

        try:
            ocr_data = pytesseract.image_to_data(
                pil_image,
                lang=self._lang,
                output_type=pytesseract.Output.DICT,
            )
        except Exception as e:
            logger.warning(f"Tesseract lỗi: {e}")
            return []

        words: List[dict] = []
        for i in range(len(ocr_data["text"])):
            txt = str(ocr_data["text"][i]).strip()
            conf = float(ocr_data["conf"][i])
            if not txt or conf < 40.0:
                continue
            words.append({
                "text": txt,
                "x0": float(ocr_data["left"][i]) * scale,
                "top": float(ocr_data["top"][i]) * scale,
                "x1": (float(ocr_data["left"][i]) + float(ocr_data["width"][i])) * scale,
                "bottom": (float(ocr_data["top"][i]) + float(ocr_data["height"][i])) * scale,
            })

        logger.info(f"Tesseract nhận dạng được {len(words)} words")
        return words
