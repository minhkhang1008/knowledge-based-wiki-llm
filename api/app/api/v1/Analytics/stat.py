from fastapi import APIRouter

router = APIRouter()

@router.get("/api/stats")
def getStats():
    return "Test success"