from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.api.v1 import articles, qa, search, wiki_articles, stats
from app.core.exceptions import (
    ArticleNotFound,
    DuplicateDocumentError,
    InvalidRequest,
    AIModelOfflineException,
    UnexpectedError
)
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
app.include_router(stats.router, tags=["Stats"])


@app.get("/")
def root():
    return {
        "message": "Hệ thống Wiki LLM đang hoạt động!"
    }

@app.exception_handler(ArticleNotFound)
async def article_not_found(
    request: Request,
    exc: ArticleNotFound
):
    response = ErrorResponse(
        success = False,
        data = None,
        message = "Article không tồn tại",
        error = ErrorFormat(
            code = "ARTICLE_NOT_FOUND",
            detail = str(exc)
        )
    )
    return JSONResponse(
        status_code = status.HTTP_404_NOT_FOUND,
        content = response.model_dump()
    )

@app.exception_handler(DuplicateDocumentError)
async def duplicate_document_error(
    request: Request,
    exc: DuplicateDocumentError
):
    response = ErrorResponse(
        success = False,
        data = None,
        message = "Trùng document_id",
        code = ErrorFormat(
            code = "DUPLICATE_DOCUMENT_ERROR",
            detail = str(exc)
        )
    )
    return JSONResponse(
        status_code = status.HTTP_409_CONFLICT,
        content = response.model_dump()
    )

@app.exception_handler(InvalidRequest)
async def invalid_request(
    request: Request,
    exc: InvalidRequest
):
    response = ErrorResponse(
        success = False,
        data = None,
        message = "Request sai",
        error = ErrorFormat(
            code = "INVALID_REQUEST",
            detail = str(exc)
        )
    )
    return JSONResponse(
        status_code = status.HTTP_422_UNPROCESSABLE_CONTENT,
        content = response.model_dump()
    )

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
        )
    )

    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content=response.model_dump()
    )

@app.exception_handler(UnexpectedError)
async def unexpected_error(
    request: Request,
    exc: UnexpectedError
):
    response = ErrorResponse(
        success = False,
        data = None,
        message = "Lỗi không dự kiến",
        error = ErrorFormat(
            code = "UNEXPECTED_ERROR",
            detail = str(exc)
        )
    )
    return JSONResponse(
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR,
        content = response.model_dump()
    )