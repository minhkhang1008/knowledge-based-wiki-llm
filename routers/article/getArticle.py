from fastapi import APIRouter

router = APIRouter()

@router.get("/api/article")
def getArticle(search: str):
    return "Test success"