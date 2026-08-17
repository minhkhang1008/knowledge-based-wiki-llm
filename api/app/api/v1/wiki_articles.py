from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.repositories.article_repository import (
    DuplicateDocumentError,
    create_article,
    delete_article,
    get_article_by_id,
    list_articles,
    update_article,
    upsert_article_by_document_id,
)
from app.schemas.article import (
    ArticleCreate,
    ArticleResponse,
    ArticleUpdate,
)
from app.schemas.ErrorFormat import ErrorFormat
from app.schemas.ErrorResponse import ErrorResponse


router = APIRouter()


def serialize_article(article) -> dict:
    return ArticleResponse.model_validate(article).model_dump(
        mode="json"
    )


def article_not_found_response(article_id: str) -> JSONResponse:
    response = ErrorResponse(
        success=False,
        data=None,
        message="Article không tồn tại",
        error=ErrorFormat(
            code="ARTICLE_NOT_FOUND",
            detail=f"Không tồn tại article với id {article_id}",
        ),
    )

    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content=response.model_dump(),
    )


@router.post("")
async def create_article_endpoint(
    data: ArticleCreate,
    db: AsyncSession = Depends(get_db),
):
    try:
        article = await create_article(db, data)

        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content={
                "success": True,
                "data": serialize_article(article),
                "message": "Tạo article thành công",
                "error": None,
            },
        )

    except DuplicateDocumentError as exc:
        response = ErrorResponse(
            success=False,
            data=None,
            message="Article đã tồn tại",
            error=ErrorFormat(
                code="DUPLICATE_DOCUMENT",
                detail=str(exc),
            ),
        )

        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content=response.model_dump(),
        )


@router.get("")
async def get_articles(
    skip: int = 0,
    limit: int = 20,
    search: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    articles = await list_articles(
        db,
        skip=skip,
        limit=limit,
        search=search,
    )

    return {
        "success": True,
        "data": [
            serialize_article(article)
            for article in articles
        ],
        "message": "Lấy danh sách article thành công",
        "error": None,
    }


@router.get("/{article_id}")
async def get_article(
    article_id: str,
    db: AsyncSession = Depends(get_db),
):
    article = await get_article_by_id(db, article_id)

    if article is None:
        return article_not_found_response(article_id)

    return {
        "success": True,
        "data": serialize_article(article),
        "message": "Lấy article thành công",
        "error": None,
    }


@router.put("/{article_id}")
async def update_article_endpoint(
    article_id: str,
    data: ArticleUpdate,
    db: AsyncSession = Depends(get_db),
):
    article = await update_article(db, article_id, data)

    if article is None:
        return article_not_found_response(article_id)

    return {
        "success": True,
        "data": serialize_article(article),
        "message": "Cập nhật article thành công",
        "error": None,
    }


@router.delete("/{article_id}")
async def delete_article_endpoint(
    article_id: str,
    db: AsyncSession = Depends(get_db),
):
    deleted = await delete_article(db, article_id)

    if not deleted:
        return article_not_found_response(article_id)

    return {
        "success": True,
        "data": None,
        "message": "Xóa article thành công",
        "error": None,
    }


@router.put("/by-document/{document_id}")
async def upsert_article_endpoint(
    document_id: str,
    data: ArticleCreate,
    db: AsyncSession = Depends(get_db),
):
    payload = data.model_dump()
    payload["document_id"] = document_id

    article = await upsert_article_by_document_id(
        db,
        payload,
    )

    return {
        "success": True,
        "data": serialize_article(article),
        "message": "Upsert article thành công",
        "error": None,
    }
