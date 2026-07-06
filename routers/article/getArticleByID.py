from fastapi import APIRouter

router = APIRouter()
    
@router.get("/api/articles/{id}")
def getArticleByID(id : str):
    success = True
    data = {
        "id" : "test",
        "title" : "test",
        "content" : "test",
        "category_id" : "test",
        "document_id" : "test",
        "updated_at" : "test",
    }
    if (success):
        return {
            "success" : success,
            "data" : data,
            "message" : "Lấy thông tin chi tiết bài viết thành công",
            "error" : None
        }
    
    return {
        "success" : success,
        "data" : None,
        "message" : "Thao tác thất bại",
        "error" : {
            "code" : "ARTICLE_NOT_FOUND",
            "detail" : "Bài viết với ID không tồn trên hệ thống"
        }
    }