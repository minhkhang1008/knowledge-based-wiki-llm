from fastapi import APIRouter

router = APIRouter()

@router.put("/api/article/{id}")
def updateArticle(id : str):
    return "Test success"