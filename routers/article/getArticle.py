from fastapi import APIRouter
from typing import Optional
from api.app.models.article import get_all_articles

router = APIRouter()

@router.get("/api/article")
async def list_article(skip: int = 0, limit: int = 20, search: Optional[str] = None):
    results = await get_all_articles(skip, limit, search)
    return {
        "success" : True,
        "data" : list(results),
        "message" : "Lấy danh sách bài viết thành công.",
        "error" : None
    }
