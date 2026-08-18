from contextlib import asynccontextmanager

import logging
import os

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1 import articles, qa, search, wiki_articles, stats
from app.core.exceptions import (
    AIModelOfflineException,
    EmptyEmbeddingError,
    InvalidResponseError,
    ModelNotFoundError,
    RequestTimeoutError,
)
from app.core.database import close_db, init_db
from app.repositories.article_repository import DuplicateDocumentError
from app.schemas.ErrorFormat import ErrorFormat
from app.schemas.ErrorResponse import ErrorResponse


logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    await init_db()
    yield
    await close_db()


app = FastAPI(
    title="Knowledge Based Wiki LLM API",
    description="API for parsing presentations and RAG",
    version="1.0.0",
    lifespan=lifespan,
)

cors_origins = [
    origin.strip()
    for origin in os.getenv(
        "CORS_ORIGINS",
        "http://localhost:5173,http://localhost:3000",
    ).split(",")
    if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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


@app.get("/health")
def health():
    return {"status": "ok"}

@app.exception_handler(DuplicateDocumentError)
async def duplicate_document_error(
    request: Request,
    exc: DuplicateDocumentError
):
    response = ErrorResponse(
        success = False,
        data = None,
        message = "Trùng document_id",
        error = ErrorFormat(
            code = "DUPLICATE_DOCUMENT",
            detail = str(exc)
        )
    )
    return JSONResponse(
        status_code = status.HTTP_409_CONFLICT,
        content = response.model_dump()
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
):
    response = ErrorResponse(
        success = False,
        data = None,
        message = "Request sai định dạng dữ liệu",
        error = ErrorFormat(
            code = "VALIDATION_ERROR",
            detail = str(exc.errors()),
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


@app.exception_handler(ModelNotFoundError)
async def model_not_found_exception(
    request: Request,
    exc: ModelNotFoundError,
):
    response = ErrorResponse(
        success=False,
        data=None,
        message="Model AI chưa được cài đặt",
        error=ErrorFormat(code="AI_MODEL_NOT_FOUND", detail=str(exc)),
    )
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content=response.model_dump(),
    )


@app.exception_handler(RequestTimeoutError)
async def ai_timeout_exception(
    request: Request,
    exc: RequestTimeoutError,
):
    response = ErrorResponse(
        success=False,
        data=None,
        message="Yêu cầu AI hết thời gian chờ",
        error=ErrorFormat(code="AI_TIMEOUT", detail=str(exc)),
    )
    return JSONResponse(
        status_code=status.HTTP_504_GATEWAY_TIMEOUT,
        content=response.model_dump(),
    )


@app.exception_handler(InvalidResponseError)
@app.exception_handler(EmptyEmbeddingError)
async def invalid_ai_response_exception(
    request: Request,
    exc: InvalidResponseError | EmptyEmbeddingError,
):
    response = ErrorResponse(
        success=False,
        data=None,
        message="Model AI trả về dữ liệu không hợp lệ",
        error=ErrorFormat(code="AI_INVALID_RESPONSE", detail=str(exc)),
    )
    return JSONResponse(
        status_code=status.HTTP_502_BAD_GATEWAY,
        content=response.model_dump(),
    )

@app.exception_handler(Exception)
async def unexpected_exception_handler(
    request: Request,
    exc: Exception,
):
    logger.error(
        "Unhandled API error",
        exc_info=(type(exc), exc, exc.__traceback__),
    )
    response = ErrorResponse(
        success = False,
        data = None,
        message = "Lỗi không dự kiến",
        error = ErrorFormat(
            code = "INTERNAL_SERVER_ERROR",
            detail = "Unexpected server error"
        )
    )
    return JSONResponse(
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR,
        content = response.model_dump()
    )
