from __future__ import annotations

import logging
import os
import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import (
    AIModelOfflineException,
    EmptyEmbeddingError,
    InvalidResponseError,
    ModelNotFoundError,
    RequestTimeoutError,
)
from app.schemas.article import ArticleResponse
from app.schemas.ingestion import (
    IngestionData,
    IngestionResponse,
    SupportedFormatsData,
    SupportedFormatsResponse,
)
from app.services.document_ingestion_service import (
    ingest_document,
    supported_ingestion_extensions,
)


router = APIRouter()
logger = logging.getLogger(__name__)
MAX_UPLOAD_SIZE_MB = int(os.getenv("MAX_UPLOAD_SIZE_MB", "25"))
MAX_UPLOAD_BYTES = MAX_UPLOAD_SIZE_MB * 1024 * 1024


async def _save_upload(file: UploadFile, destination: Path) -> None:
    written = 0
    with destination.open("wb") as output:
        while chunk := await file.read(1024 * 1024):
            written += len(chunk)
            if written > MAX_UPLOAD_BYTES:
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail=f"Tệp vượt quá giới hạn {MAX_UPLOAD_SIZE_MB} MB.",
                )
            output.write(chunk)


def _safe_filename(filename: str | None) -> str:
    name = Path(filename or "").name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Tên tệp không hợp lệ.")
    return name


async def _ingest_upload(
    file: UploadFile,
    title: str | None,
    db: AsyncSession,
) -> IngestionResponse:
    filename = _safe_filename(file.filename)
    extension = Path(filename).suffix.lower()
    supported = supported_ingestion_extensions()
    if extension not in supported:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail={
                "message": f"Định dạng '{extension or '(không có)'}' chưa sẵn sàng.",
                "supported_extensions": supported,
            },
        )

    try:
        with tempfile.TemporaryDirectory(prefix="kbw-upload-") as temp_dir:
            temp_path = Path(temp_dir) / filename
            await _save_upload(file, temp_path)
            result = await ingest_document(
                db,
                temp_path,
                source_file=filename,
                title=title,
            )
    except HTTPException:
        raise
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except (
        AIModelOfflineException,
        EmptyEmbeddingError,
        InvalidResponseError,
        ModelNotFoundError,
        RequestTimeoutError,
    ):
        raise
    except Exception as exc:
        logger.exception("Document ingestion failed for %s", filename)
        raise HTTPException(
            status_code=500,
            detail="Không thể ingest tài liệu. Không có thay đổi dở dang được giữ lại.",
        ) from exc
    finally:
        await file.close()

    return IngestionResponse(
        data=IngestionData(
            article=ArticleResponse.model_validate(result.article),
            document_id=result.document_id,
            chunk_count=result.chunk_count,
        ),
        message="Ingest tài liệu thành công",
    )


@router.get("/supported-formats", response_model=SupportedFormatsResponse)
async def get_supported_formats() -> SupportedFormatsResponse:
    return SupportedFormatsResponse(
        data=SupportedFormatsData(
            extensions=supported_ingestion_extensions(),
            max_upload_size_mb=MAX_UPLOAD_SIZE_MB,
        ),
        message="Lấy định dạng ingest thành công",
    )


@router.post("/upload", response_model=IngestionResponse, status_code=201)
async def upload_document(
    file: UploadFile = File(...),
    title: str | None = Form(default=None),
    db: AsyncSession = Depends(get_db),
) -> IngestionResponse:
    return await _ingest_upload(file, title, db)


@router.post(
    "/upload-presentation",
    response_model=IngestionResponse,
    status_code=201,
    deprecated=True,
)
async def upload_presentation(
    file: UploadFile = File(...),
    title: str | None = Form(default=None),
    db: AsyncSession = Depends(get_db),
) -> IngestionResponse:
    if Path(_safe_filename(file.filename)).suffix.lower() not in {".ppt", ".pptx"}:
        raise HTTPException(status_code=400, detail="Chỉ hỗ trợ tệp PowerPoint.")
    return await _ingest_upload(file, title, db)
