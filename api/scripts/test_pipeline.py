import sys
import os
from pathlib import Path
from unittest.mock import patch, MagicMock

# Trỏ đường dẫn để Python nhận diện app
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.services.document_parser.pipeline import DocumentParserPipeline

def run_pipeline_test():
    print("=== BẮT ĐẦU TEST BỘ ĐIỀU PHỐI PIPELINE (SQUAD 1) ===\n")
    
    # 1. Tạo file ảnh giả lập để test
    test_file_path = "storage/test_dummy_image.png"
    os.makedirs("storage", exist_ok=True)
    with open(test_file_path, "wb") as f:
        f.write(b"Fake image data for testing pipeline SHA256")
        
    print("⏳ TEST: Khởi chạy luồng xử lý file qua Pipeline...")
    
    try:
        # Giả lập hàm get_converter để nó không gọi thật xuống OCR
        # Thay vào đó, trả về một hàm dummy sinh ra chuỗi Markdown
        dummy_converter_func = MagicMock(return_value="> Nội dung trích xuất giả lập từ Mock Converter")
        
        with patch('app.services.document_parser.pipeline.get_converter', return_value=dummy_converter_func):
            
            pipeline = DocumentParserPipeline(output_base_dir="storage/extracted_data")
            
            # Chạy hàm process_file
            result_md_path = pipeline.process_file(test_file_path)
            
            # Kiểm tra kết quả
            if os.path.exists(result_md_path):
                print(f"   ✅ Thành công: File Markdown đã được tạo tại {result_md_path}")
                
                # Đọc thử file xem có ghi đúng dữ liệu không
                with open(result_md_path, "r", encoding="utf-8") as f:
                    content = f.read()
                    if "Mock Converter" in content:
                        print("   ✅ Thành công: Dữ liệu luân chuyển qua ProcessPoolExecutor hoàn hảo!")
                    else:
                        print("   ❌ Thất bại: File được tạo nhưng ghi sai nội dung.")
            else:
                print("   ❌ Thất bại: Pipeline chạy xong nhưng không thấy file output đâu.")
                
    except Exception as e:
        print(f"   ❌ Lỗi hệ thống khi test Pipeline: {e}")
    finally:
        # Dọn dẹp file test
        if os.path.exists(test_file_path):
            os.remove(test_file_path)

if __name__ == "__main__":
    run_pipeline_test()