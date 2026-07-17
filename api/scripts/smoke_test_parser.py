import os
import sys
from pathlib import Path

# Thêm thư mục api vào sys.path để kích hoạt absolute import bắt đầu bằng 'app'
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.services.document_parser import DocumentParserPipeline

def run_smoke_test():
    print("=== KHỞI CHẠY SMOKE TEST: DOCUMENT PARSER PIPELINE ===")
    
    # 1. Khởi tạo pipeline, kết quả trích xuất sẽ lưu tại storage/test_extracted
    pipeline = DocumentParserPipeline(output_base_dir="storage/test_extracted")
    
    # 2. Định nghĩa danh sách file mẫu để quét dữ liệu (Cần đặt file thật vào các đường dẫn này)
    test_files = [
        "tests/test_data/sample.docx",
        "tests/test_data/sample.xlsx",
        "tests/test_data/sample.pptx",
        "tests/test_data/legacy_sample.doc"  # Kiểm thử luồng unoserver
    ]
    
    for file_path in test_files:
        if not os.path.exists(file_path):
            print(f"⚠️ Bỏ qua: Không tìm thấy file mẫu tại vị trí '{file_path}'")
            continue
            
        print(f"\n🔄 Tiến trình xử lý file: {file_path}")
        try:
            # Thực thi pipeline
            result_md_path = pipeline.process_file(file_path)
            
            print(f"✅ Trích xuất thành công!")
            print(f"📂 Thư mục đầu ra: {os.path.dirname(result_md_path)}")
            print(f"📝 File Markdown kết quả: {result_md_path}")
            
        except Exception as e:
            print(f"❌ Lỗi xử lý file {file_path}: {str(e)}")

if __name__ == "__main__":
    run_smoke_test()