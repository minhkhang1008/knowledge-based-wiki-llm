import os
import shutil
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.services.document_parser.pipeline import DocumentParserPipeline

router = APIRouter()
pipeline = DocumentParserPipeline()

@router.post("/upload-presentation")
async def upload_presentation(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """Endpoint tiếp nhận file PowerPoint, tự động convert sang Markdown phục vụ RAG."""
    # Kiểm tra phần mở rộng file
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in [".pptx", ".ppt"]:
        raise HTTPException(status_code=400, detail="Chỉ hỗ trợ tệp tin định dạng .ppt hoặc .pptx")
        
    # Tạo thư mục tạm để chứa file vừa upload lên
    temp_dir = "storage/temp"
    os.makedirs(temp_dir, exist_ok=True)
    temp_file_path = os.path.join(temp_dir, file.filename)
    
    try:
        # Ghi file upload vào ổ đĩa tạm
        with open(temp_file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        # Đẩy file vào pipeline xử lý đa tiến trình chuyên sâu
        markdown_file_path = pipeline.process_file(temp_file_path)
        
        # Đọc nội dung markdown vừa sinh ra để trả phản hồi hoặc bàn giao cho Squad 2
        with open(markdown_file_path, "r", encoding="utf-8") as f:
            markdown_content = f.read()
            
        # Khối kết nối kiến trúc: Trả kết quả về cho hệ thống
        return {
            "status": "success",
            "filename": file.filename,
            "markdown_path": markdown_file_path,
            "content_preview": markdown_content[:500]  # Trả về một đoạn preview ngắn
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
        
    finally:
        # Dọn dẹp tệp tin tạm thời sau khi xử lý xong để giải phóng bộ nhớ đĩa
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)