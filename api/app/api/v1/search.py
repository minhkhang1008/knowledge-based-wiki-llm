from fastapi import APIRouter

router = APIRouter()

@router.post("/api/search")
def searchFunc():
    return "Test success"