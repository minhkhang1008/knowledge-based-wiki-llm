import os
import hashlib
import subprocess
import logging
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor

from app.services.document_parser.converter_registry import get_converter
import app.services.document_parser.docx_converter
import app.services.document_parser.excel_converter
import app.services.document_parser.pptx_core
import app.services.document_parser.pdf_converter
import app.services.document_parser.image_converter  # đăng ký .png .jpg .jpeg .bmp .tiff .webp .gif

logger = logging.getLogger("pipeline")

# Định dạng không cần LibreOffice convert — xử lý trực tiếp
_DIRECT_FORMATS = {
    ".pdf", ".docx", ".xlsx", ".xlsm", ".pptx",
    ".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".tif", ".webp", ".gif",
}

# Định dạng legacy cần LibreOffice convert trước
_LEGACY_FORMATS = {
    ".ppt": "pptx",
    ".doc": "docx",
    ".xls": "xlsx",
}

class DocumentParserPipeline:
    def __init__(self, output_base_dir: str | None = None):
        self.output_base_dir = output_base_dir or os.getenv(
            "EXTRACTED_DATA_DIR",
            "storage/extracted_data",
        )
        os.makedirs(self.output_base_dir, exist_ok=True)

    @staticmethod
    def is_supported(file_path: str) -> bool:
        """Kiểm tra xem file có được hỗ trợ không."""
        ext = Path(file_path).suffix.lower()
        return ext in _DIRECT_FORMATS or ext in _LEGACY_FORMATS

    @staticmethod
    def calculate_sha256(file_path: str) -> str:
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

    @staticmethod
    def convert_legacy_formats(file_path: str) -> str:
        """Hỗ trợ LibreOffice Headless cho .ppt, .doc, .xls sang định dạng hiện đại."""
        path_obj = Path(file_path)
        ext = path_obj.suffix.lower()

        if ext not in _LEGACY_FORMATS:
            return file_path

        new_ext = _LEGACY_FORMATS[ext]
        new_path = str(path_obj.with_suffix(f".{new_ext}"))

        cmd = [
            "libreoffice",
            "--headless",
            "--convert-to", new_ext,
            file_path,
            "--outdir", str(path_obj.parent)
        ]

        try:
            subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            return new_path
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Lỗi khi convert qua LibreOffice: {e.stderr.decode()}")
        except FileNotFoundError:
            raise RuntimeError(
                "Hệ thống không tìm thấy 'libreoffice'. "
                "Vui lòng đảm bảo đã cài đặt LibreOffice trên máy."
            )

    @staticmethod
    def _worker_process(file_path: str, output_dir: str) -> str:
        target_path = DocumentParserPipeline.convert_legacy_formats(file_path)
        source_path = Path(target_path)

        converter = get_converter(source_path.suffix)
        if not converter:
            supported = sorted(_DIRECT_FORMATS | set(_LEGACY_FORMATS.keys()))
            raise ValueError(
                f"Định dạng '{source_path.suffix}' chưa được hỗ trợ. "
                f"Các định dạng được hỗ trợ: {', '.join(supported)}"
            )

        logger.info(f"Đang xử lý: {source_path.name} → {source_path.suffix}")
        markdown_text = converter(source_path, output_dir)

        # Xóa file tạm sau khi convert legacy format
        if target_path != file_path and os.path.exists(target_path):
            os.remove(target_path)

        return markdown_text

    def process_file(self, file_path: str) -> str:
        """
        Xử lý file → Markdown và lưu vào output_base_dir.
        Trả về đường dẫn file .md đã lưu.

        Luồng:
        1. Tính SHA256 để tạo thư mục output duy nhất (tránh xử lý lại file giống nhau)
        2. Chạy converter trong ProcessPoolExecutor để tránh block event loop
        3. Lưu kết quả Markdown ra file
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File không tồn tại: {file_path}")

        if not self.is_supported(file_path):
            ext = Path(file_path).suffix.lower()
            raise ValueError(f"Định dạng '{ext}' chưa được hỗ trợ.")

        file_hash = self.calculate_sha256(file_path)
        unique_output_dir = os.path.join(self.output_base_dir, file_hash)

        with ProcessPoolExecutor(max_workers=1) as executor:
            future = executor.submit(self._worker_process, file_path, unique_output_dir)
            try:
                markdown_result = future.result(timeout=None)

                md_file_path = os.path.join(unique_output_dir, "document.md")
                os.makedirs(unique_output_dir, exist_ok=True)
                with open(md_file_path, "w", encoding="utf-8") as f:
                    f.write(markdown_result)

                logger.info(f"Đã lưu: {md_file_path}")
                return md_file_path
            except Exception as e:
                raise RuntimeError(f"Lỗi hệ thống khi phân tích file: {str(e)}") from e
