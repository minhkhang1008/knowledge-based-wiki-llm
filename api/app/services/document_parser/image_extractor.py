import os
from pptx.enum.shapes import MSO_SHAPE_TYPE

class PptxImageExtractor:
    _reader = None

    @classmethod
    def _get_reader(cls):
        if cls._reader is None:
            try:
                import easyocr
                print("\n🧠 Đang nạp bộ quét EasyOCR")
                # Khởi tạo mô hình hỗ trợ song ngữ: Tiếng Việt ('vi') và Tiếng Anh ('en')
                cls._reader = easyocr.Reader(['vi', 'en'], gpu=True)
                print("✅ Nạp EasyOCR thành công!")
            except Exception as e:
                print(f"\n⚠️ Lỗi khởi tạo EasyOCR: {e}")
                cls._reader = False
        return cls._reader

    @staticmethod
    def extract(shape, output_dir: str, slide_idx: int, shape_idx: int) -> str:
        """Trích xuất ảnh và dùng EasyOCR quét chữ đa nền tảng."""
        if shape.shape_type != MSO_SHAPE_TYPE.PICTURE:
            return ""
            
        os.makedirs(output_dir, exist_ok=True)
        image = shape.image
        ext = image.ext
        
        image_filename = f"slide_{slide_idx}_shape_{shape_idx}.{ext}"
        image_path = os.path.join(output_dir, image_filename)
        
        with open(image_path, "wb") as f:
            f.write(image.blob)
            
        alt_text = getattr(shape, "description", "").strip()
        if not alt_text:
            alt_text = shape.name if shape.name else f"Image_S{slide_idx}_P{shape_idx}"
            
        ocr_result_text = ""
        reader = PptxImageExtractor._get_reader()
        
        if reader:
            print(f"🔍 EasyOCR đang quét ảnh: {image_filename}...")
            try:
                results = reader.readtext(image_path)
                
                extracted_lines = []
                for res in results:
                    text = res[1].strip()
                    if text and len(text) > 1:
                        extracted_lines.append(text)
                        
                if extracted_lines:
                    ocr_result_text = "\n> ".join(extracted_lines)
            except Exception as e:
                print(f"⚠️ Lỗi xử lý OCR tại {image_filename}: {e}")
                
        markdown_output = f"![{alt_text}]({image_path})\n"
        if ocr_result_text:
            markdown_output += f"> 🖼️ **Nội dung chữ trong ảnh (EasyOCR):**\n> {ocr_result_text}\n"
            
        return markdown_output + "\n"