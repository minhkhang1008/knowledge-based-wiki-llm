import pytest
import os
import shutil
from app.services.document_parser.pptx_core import PptxCoreParser

def test_pptx_core_parser_extracts_all_components():
    test_file = "tests/test_data/test_pptx_data.pptx"
    custom_image_dir = "tests/test_data/extracted_images_test"
    
    # Clean up thư mục test cũ nếu có
    if os.path.exists(custom_image_dir):
        shutil.rmtree(custom_image_dir)
        
    parser = PptxCoreParser(test_file, images_output_dir=custom_image_dir)
    md_output = parser.parse()
    
    # 1. Kiểm tra Text & Table
    assert "---" in md_output
    assert "## Trọng tâm: Mạch sử dụng IC NE555" in md_output
    
    # 2. Kiểm tra Cú pháp hình ảnh trong Markdown
    assert "![" in md_output
    assert "tests/test_data/extracted_images_test/slide_" in md_output
    
    # 3. Kiểm tra file hình ảnh thực tế có tồn tại trên ổ đĩa hay không
    assert os.path.exists(custom_image_dir)
    extracted_files = os.listdir(custom_image_dir)
    assert len(extracted_files) > 0
    
    # Dọn dẹp môi trường sau khi test xong
    shutil.rmtree(custom_image_dir)

def test_pipeline_integration_flow():
    from app.services.document_parser.pipeline import DocumentParserPipeline
    import os
    
    test_file = "tests/test_data/test_pptx_data.pptx"
    pipeline = DocumentParserPipeline(output_base_dir="tests/test_data/pipeline_output")
    
    # Thực thi toàn bộ pipeline cấu trúc
    md_file_result = pipeline.process_file(test_file)
    
    # Kiểm tra xem file kết quả có tồn tại không
    assert os.path.exists(md_file_result)
    assert md_file_result.endswith("document.md")
    
    # Đọc nội dung và check xem có Speaker Notes hay không
    with open(md_file_result, "r", encoding="utf-8") as f:
        content = f.read()
        assert "## Trọng tâm: Mạch sử dụng IC NE555" in content
        # Nếu slide test của bạn có speaker notes, uncomment dòng dưới để assert
        # assert "> **Speaker Notes:**" in content

    # Clean up sau khi test
    import shutil
    shutil.rmtree("tests/test_data/pipeline_output")