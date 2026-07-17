from abc import ABC, abstractmethod
from typing import List


class BaseOCREngine(ABC):
    """
    Interface trừu tượng cho tất cả OCR engine.
    Tuân theo Open/Closed Principle: thêm engine mới chỉ cần tạo class mới,
    không sửa code hiện tại.
    """

    @abstractmethod
    def extract_words(self, pil_image, scale: float = 1.0) -> List[dict]:
        """
        Trích xuất danh sách words từ PIL Image.

        Args:
            pil_image: PIL.Image object của trang PDF đã render
            scale: hệ số tỷ lệ để quy đổi tọa độ pixel → point PDF (72/resolution)

        Returns:
            List[dict] mỗi phần tử có dạng:
            {
                "text": str,
                "x0": float,   # tọa độ trái (point)
                "top": float,  # tọa độ trên (point)
                "x1": float,   # tọa độ phải (point)
                "bottom": float  # tọa độ dưới (point)
            }
        """
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Tên engine để log."""
        pass
