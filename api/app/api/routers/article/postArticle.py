from fastapi import APIRouter

router = APIRouter()

@router.post("/api/articles")
def createArticle():
    return {
        "success": True,
        "data": [
            {
                "id": "wiki_03",
                "title": "Tổng quan về RAG",
                "category": "ai"
            }
        ],
        "message": "Tạo bài viết mới thành công.",
        "error" : None
    }