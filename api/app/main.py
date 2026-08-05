from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.api.v1 import articles, qa, search, wiki_articles
from app.core.exceptions import AIModelOfflineException
from app.schemas.ErrorFormat import ErrorFormat
from app.schemas.ErrorResponse import ErrorResponse


app = FastAPI(
    title="Knowledge Based Wiki LLM API",
    description="API for parsing presentations and RAG",
    version="1.0.0",
)

app.include_router(
    articles.router,
    prefix="/api/v1/articles",
    tags=["Articles"],
)
app.include_router(qa.router, tags=["QA"])
app.include_router(search.router, tags=["Search"])
app.include_router(
    wiki_articles.router,
    prefix="/api/articles",
    tags=["Wiki Articles"],
)


@app.get("/")
def root():
    return {
        "message": "Hệ thống Wiki LLM đang hoạt động!"
    }


@app.exception_handler(AIModelOfflineException)
async def ai_model_offline_exception(
    request: Request,
    exc: AIModelOfflineException,
):
    response = ErrorResponse(
        success=False,
        data=None,
        message="Hệ thống AI hiện đang ngoại tuyến",
        error=ErrorFormat(
            code="AI_ENGINE_OFFLINE",
            detail=str(exc),
        ),
    )

    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content=response.model_dump(),
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
):
    response = ErrorResponse(
        success=False,
        data=None,
        message="Request sai định dạng dữ liệu",
        error=ErrorFormat(
            code="VALIDATION_ERROR",
            detail=str(exc.errors()),
        ),
    )

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content=response.model_dump(),
    )