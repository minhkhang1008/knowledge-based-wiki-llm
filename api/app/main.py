from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from app.api.v1 import articles, qa, search
from app.core.exceptions import AIModelOfflineException

app = FastAPI(
    title="Knowledge Based Wiki LLM API",
    description="API for parsing presentations and RAG",
    version="1.0.0"
)

app.include_router(articles.router, prefix="/api/v1/articles", tags=["Articles"])
app.include_router(qa.router, tags=["QA"])
app.include_router(search.router, tags=["Search"])

@app.get("/")
def root():
    return {"message": "Hệ thống Wiki LLM đang hoạt động!"}

@app.exception_handler(AIModelOfflineException)
async def ai_mode_offline_exception(request: Request, exc: AIModelOfflineException):
    # request: bat buoc, schema de luu gia tri
    # exc: lay gia tri bao loi
    return JSONResponse(
        status_code = 503,
        content = {
            "success": False,
            "message": "Hệ thống AI hiện đang ngoại tuyến, vui lòng liên hệ quản trị viên.",
            "data": None,
            "error": {
                "code": "AI_ENGINE_OFFLINE"
            }
        }
    )
