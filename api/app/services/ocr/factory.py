import os
import logging
import threading
from app.services.ocr.base import BaseOCREngine

logger = logging.getLogger("ocr.factory")

class OCRFactory:
    _instance: BaseOCREngine | None = None
    _lock = threading.Lock()

    @staticmethod
    def get_engine() -> BaseOCREngine:
        if OCRFactory._instance is not None:
            return OCRFactory._instance

        with OCRFactory._lock:
            # Double-checked locking
            if OCRFactory._instance is not None:
                return OCRFactory._instance

            engine_type = os.getenv("OCR_ENGINE_TYPE", "easyocr").lower()
            logger.info(f"Khởi tạo OCR engine: {engine_type}")

            # ĐÃ SỬA: Thụt lề toàn bộ khối IF này vào bên trong `with _lock:`
            if engine_type == "easyocr":
                from app.services.ocr.easyocr_engine import EasyOCREngine
                OCRFactory._instance = EasyOCREngine(
                    languages=["en", "vi"],
                    gpu=os.getenv("OCR_USE_GPU", "false").lower() == "true",
                )

            elif engine_type == "tesseract":
                from app.services.ocr.tesseract_engine import TesseractEngine
                OCRFactory._instance = TesseractEngine(
                    lang=os.getenv("TESSERACT_LANG", "eng+vie"),
                )

            else:
                raise ValueError(
                    f"OCR_ENGINE_TYPE='{engine_type}' không hợp lệ. "
                    "Các giá trị được hỗ trợ: 'easyocr', 'tesseract'."
                )

        return OCRFactory._instance