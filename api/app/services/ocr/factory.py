import os
import logging
from app.services.ocr.base import BaseOCREngine

logger = logging.getLogger("ocr.factory")


class OCRFactory:
    """
    Factory tạo OCR engine dựa trên biến môi trường OCR_ENGINE_TYPE.
    Mặc định dùng EasyOCR.

    Để đổi engine, set trong .env:
        OCR_ENGINE_TYPE=easyocr    # mặc định
        OCR_ENGINE_TYPE=tesseract  # fallback
    """

    _instance: BaseOCREngine | None = None  # singleton cache

    @staticmethod
    def get_engine() -> BaseOCREngine:
        """
        Trả về OCR engine singleton.
        Engine chỉ được khởi tạo một lần trong vòng đời ứng dụng
        để tránh load lại model mỗi request.
        """
        if OCRFactory._instance is not None:
            return OCRFactory._instance

        engine_type = os.getenv("OCR_ENGINE_TYPE", "easyocr").lower()
        logger.info(f"Khởi tạo OCR engine: {engine_type}")

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

    @staticmethod
    def reset():
        """Reset singleton — dùng cho testing."""
        OCRFactory._instance = None
