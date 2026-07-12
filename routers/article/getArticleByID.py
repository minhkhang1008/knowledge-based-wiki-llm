from fastapi import APIRouter, HTTPException
from api.app.models.article import get_article_by_id

router = APIRouter()
    
@router.get("/api/articles/{id}")
async def getArticleByID(id : str):
    article = await get_article_by_id(id)
    if article is None:
        raise HTTPException(status_code=404, detail="Bài viết không tồn tại")
    return {
        "success" : True,
        "data": article,
        "message": "Lấy chi tiết bài viết thành công.",
        "error" : None
    }