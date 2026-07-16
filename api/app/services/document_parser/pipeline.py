import os
import hashlib
import subprocess
from concurrent.futures import ProcessPoolExecutor, TimeoutError
from app.services.document_parser.pptx_core import PptxCoreParser

class DocumentParserPipeline:
    def __init__(self, output_base_dir: str = "storage/extracted_data"):
        self.output_base_dir = output_base_dir
        os.makedirs(output_base_dir, exist_ok=True)

    @staticmethod
    def calculate_sha256(file_path: str) -> str:
        """Tính chữ ký số SHA-256 của file để làm Hashing Registry."""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

    @staticmethod
    def convert_ppt_to_pptx(file_path: str) -> str:
        """Gọi unoserver daemon để chuẩn hóa file .ppt cũ sang .pptx."""
        if file_path.endswith(".pptx"):
            return file_path
            
        if file_path.endswith(".ppt"):
            new_path = file_path + "x"
            # Gọi unoserver client thông qua CLI
            cmd = ["unoserver-Client", file_path, new_path]
            try:
                subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                return new_path
            except subprocess.CalledProcessError as e:
                raise RuntimeError(f"Lỗi khi convert qua unoserver: {e.stderr.decode()}")
        
        raise ValueError("Định dạng file không được hỗ trợ.")

    @staticmethod
    def _worker_process(file_path: str, output_dir: str) -> str:
        """Hàm độc lập chạy bên trong từng Worker Process biệt lập."""
        # 1. Khử định dạng cũ nếu có
        target_path = DocumentParserPipeline.convert_ppt_to_pptx(file_path)
        
        # 2. Định nghĩa thư mục lưu ảnh riêng cho file này
        images_dir = os.path.join(output_dir, "images")
        
        # 3. Tiến hành parse DOM và giải thuật hình học
        parser = PptxCoreParser(target_path, images_output_dir=images_dir)
        markdown_text = parser.parse()
        
        # Nếu là file tạm tạo ra từ .ppt, tiến hành dọn dẹp
        if target_path != file_path and os.path.exists(target_path):
            os.remove(target_path)
            
        return markdown_text

    def process_file(self, file_path: str) -> str:
        """Bao bọc tiến trình bằng Executor để xử lý độc lập không giới hạn thời gian."""
        file_hash = self.calculate_sha256(file_path)
        unique_output_dir = os.path.join(self.output_base_dir, file_hash)
        
        # Khởi chạy tiến trình công nhân biệt lập
        with ProcessPoolExecutor(max_workers=1) as executor:
            future = executor.submit(self._worker_process, file_path, unique_output_dir)
            try:
                markdown_result = future.result(timeout=None)
                
                md_file_path = os.path.join(unique_output_dir, "document.md")
                os.makedirs(unique_output_dir, exist_ok=True)
                with open(md_file_path, "w", encoding="utf-8") as f:
                    f.write(markdown_result)
                    
                return md_file_path
            except Exception as e:
                raise RuntimeError(f"Lỗi hệ thống khi phân tích file: {str(e)}")