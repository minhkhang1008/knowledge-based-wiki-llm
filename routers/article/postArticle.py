from fastapi import APIRouter

router = APIRouter()

@router.post("/api/articles")
def createArticle():
    return "Test success"