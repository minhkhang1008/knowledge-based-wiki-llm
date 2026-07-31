from fastapi import APIRouter, Depends, status, HTTPException
from fastapi.responses import JSONResponse
from typing import Optional, Any
from app.repositories.article_repository import (
    DuplicateDocumentError,
    create_article,
    delete_article,
    get_article_by_id,
    list_articles,
    update_article,
    upsert_article_by_document_id
)
from app.schemas.article import ArticleCreate, ArticleUpdate, ArticleResponse
from app.schemas.ErrorResponse import ErrorResponse
from app.schemas.ErrorFormat import ErrorFormat
from app.core.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession

class ArticleNotFound(Exception):
    pass

router = APIRouter()

@router.post("")
async def CreateArticle(data: ArticleCreate, db: AsyncSession = Depends(get_db)):
    try:
        article = await create_article(db, data)
        response_data = ArticleResponse.model_validate(article).model_dump(mode="json")

        return JSONResponse(
            status_code = status.HTTP_201_CREATED,
            content = {
                "success" : True,
                "data" : response_data,
                "message" : "Tạo article thành công",
                "error" : 1
            }
        )
    except DuplicateDocumentError as e:
        response = ErrorResponse(
            success = False,
            data = None,
            message = "Article đã tồn tại",
            error = ErrorFormat(
                code = type(e).__name__,
                detail = str(e)
            )
        )
        return JSONResponse(
            status_code = status.HTTP_409_CONFLICT, 
            content = response.model_dump()
        )

@router.get("")
async def GetArticle(skip: int = 0, limit: int = 20,
                search: Optional[str] = None, db: AsyncSession = Depends(get_db)):
    result = await list_articles(db, skip, limit, search)
    return {
        "success" : True,
        "data" : result,
        "message" : "Lấy list article thành công",
        "error" : None
    }

@router.get("/{article_id}")
async def GetArticleById(article_id: str, db: AsyncSession = Depends(get_db)):
    try:
        result = await get_article_by_id(db, article_id)

        if result == None:
            raise  ArticleNotFound()
        
        return {
            "success" : True,
            "data" : result,
            "message" : "Lấy article bằng id thành công",
            "error" : None
        }
    except ArticleNotFound:
        response = ErrorResponse(
            success = False,
            data = None,
            message = "Tìm kiếm thất bại",
            error = ErrorFormat(
                code = "404 Not Found",
                detail = f"Không tồn tại article với id là {article_id}"
            )
        )
        return JSONResponse(
            status_code = status.HTTP_404_NOT_FOUND,
            content = response.model_dump()
        )

@router.put("/{article_id}")
async def UpdateArticle(data: ArticleUpdate, article_id: str, db: AsyncSession = Depends(get_db)):
    try:
        result = await update_article(db, article_id, data)

        if result == None:
            raise ArticleNotFound()

        return {
            "success" : True,
            "data" : result,
            "message" : "Update article thành công",
            "error" : None
        }
    except ArticleNotFound:
        response = ErrorResponse(
            success = False,
            data = None,
            message = "Cập nhật article thất bại",
            error = ErrorFormat(
                code = "404 Not Found",
                detail = f"Không tòn tại article với id là {article_id}"
            )
        )
        return JSONResponse(
            status_code = status.HTTP_404_NOT_FOUND,
            content = response.model_dump()
        )

@router.delete("{article_id}")
async def DeleteArticle(article_id: str, db: AsyncSession = Depends(get_db)):
    try:
        result = delete_article(db, article_id)
        if result == None:
            raise ArticleNotFound()
        return {
            "success" : True,
            "data" : None,
            "message" : "Xóa article thành công",
            "error" : None
        }
    except ArticleNotFound:
        response = ErrorResponse(
            success = False,
            data = None,
            message = "Xóa article thất bại",
            error = ErrorFormat(
                code = "404 Not Found",
                detail = f"Không tồn tại article với id là {article_id} để xóa"
            )
        )
        return JSONResponse(
            status_code = status.HTTP_404_NOT_FOUND,
            content = response
        )

@router.put("/by-document/{document_id}")
async def upsert_with_document_id(data: ArticleCreate, db: AsyncSession = Depends(get_db)):
    result = await upsert_article_by_document_id(db, data)
    return {
        "success" : True,
        "data" : result,
        "message" : "Upsert article thành công",
        "error" : None
    }