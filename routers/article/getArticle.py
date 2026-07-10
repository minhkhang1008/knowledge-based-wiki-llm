from fastapi import APIRouter
from typing import Optional

router = APIRouter()

@router.get("/api/article")
def getArticle(search: Optional[str] = None):
    return "Test success"