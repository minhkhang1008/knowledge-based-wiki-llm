import os
import logging
from pptx.enum.shapes import MSO_SHAPE_TYPE

logger = logging.getLogger("image_extractor")


class PptxImageExtractor:
    """
    Trích xuất hình ảnh từ shape PPTX và tùy chọn OCR nội dung chữ trong ảnh.
    Dùng OCRFactory để chọn engine phù hợp (EasyOCR hoặc Tesseract) qua env var.
    """

    @staticmethod
    def extract(shape, output_dir: str, slide_idx: int, shape_idx: int) -> str:
        """
        Trích xuất ảnh từ shape PICTURE, lưu file và trả về Markdown.
        Nếu OCR engine khả dụng, thêm nội dung text nhận dạng được vào output.

        Returns:
            Markdown string dạng: ![alt](relative_path)\n> text...
        """
        if shape.shape_type != MSO_SHAPE_TYPE.PICTURE:
            return ""

        os.makedirs(output_dir, exist_ok=True)

        image = shape.image
        ext = image.ext
        image_filename = f"slide_{slide_idx}_shape_{shape_idx}.{ext}"
        image_path = os.path.join(output_dir, image_filename)

        with open(image_path, "wb") as f:
            f.write(image.blob)

        # Alt text: ưu tiên description của shape, fallback về tên shape
        alt_text = getattr(shape, "description", "").strip()
        if not alt_text:
            alt_text = shape.name if shape.name else f"Image_S{slide_idx}_P{shape_idx}"

        # Dùng relative path trong markdown để portable
        relative_path = os.path.relpath(image_path, start=os.path.dirname(output_dir))
        markdown_output = f"![{alt_text}]({relative_path})\n"

        # OCR nội dung chữ trong ảnh (nếu có engine)
        ocr_text = PptxImageExtractor._run_ocr(image_path)
        if ocr_text:
            markdown_output += f"> **Nội dung chữ trong ảnh:**\n> {ocr_text}\n"

        return markdown_output + "\n"

    @staticmethod
    def _run_ocr(image_path: str) -> str:
        """Chạy OCR trên file ảnh, dùng shared utility."""
        from app.services.ocr.ocr_utils import ocr_image_file_to_text
        return ocr_image_file_to_text(image_path)
