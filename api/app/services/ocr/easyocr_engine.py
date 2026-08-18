import logging
from typing import List

from app.services.ocr.base import BaseOCREngine

logger = logging.getLogger("ocr.easyocr")


class EasyOCREngine(BaseOCREngine):
    """
    OCR engine dùng EasyOCR — primary engine.
    Không cần binary riêng, chạy thuần Python + PyTorch (đã có trong requirements.txt).
    Hỗ trợ tiếng Việt và tiếng Anh built-in.

    Reader được khởi tạo lazy (lần đầu gọi) và cache lại để tái dùng giữa các trang.
    """

    def __init__(self, languages: List[str] = None, gpu: bool = False):
        self._languages = languages or ["en", "vi"]
        self._gpu = gpu
        self._reader = None  # lazy init

    def _get_reader(self):
        if self._reader is None:
            try:
                import easyocr
                logger.info(
                    f"Khởi tạo EasyOCR reader (languages={self._languages}, gpu={self._gpu}). "
                    "Lần đầu sẽ tải model, vui lòng chờ..."
                )
                self._reader = easyocr.Reader(
                    self._languages,
                    gpu=self._gpu,
                    verbose=False,
                )
                logger.info("EasyOCR reader sẵn sàng.")
            except ImportError as e:
                raise ImportError(
                    "EasyOCR chưa được cài. Chạy: pip install easyocr"
                ) from e
        return self._reader

    @property
    def name(self) -> str:
        return "easyocr"

    def extract_words(self, pil_image, scale: float = 1.0) -> List[dict]:
        """
        Nhận dạng text từ PIL Image bằng EasyOCR.
        EasyOCR trả về bounding box dạng 4 điểm góc, cần quy đổi sang
        format (x0, top, x1, bottom) để tương thích với phần còn lại của pipeline.
        """
        import numpy as np

        reader = self._get_reader()
        img_array = np.array(pil_image)

        try:
            results = reader.readtext(img_array)
        except Exception as e:
            logger.warning(f"EasyOCR.readtext lỗi: {e}")
            return []

        words: List[dict] = []
        for bbox_points, text, conf in results:
            text = text.strip()
            if not text or conf < 0.4:
                continue
            # bbox_points: [[x1,y1],[x2,y1],[x2,y2],[x1,y2]] (pixel)
            xs = [p[0] for p in bbox_points]
            ys = [p[1] for p in bbox_points]
            words.append({
                "text": text,
                "x0": min(xs) * scale,
                "top": min(ys) * scale,
                "x1": max(xs) * scale,
                "bottom": max(ys) * scale,
                "confidence": float(conf),
            })

        logger.info(f"EasyOCR nhận dạng được {len(words)} vùng text")
        return words
