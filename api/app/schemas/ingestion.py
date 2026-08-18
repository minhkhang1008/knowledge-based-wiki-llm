from pydantic import BaseModel, ConfigDict

from app.schemas.article import ArticleResponse


class SupportedFormatsData(BaseModel):
    extensions: list[str]
    max_upload_size_mb: int


class SupportedFormatsResponse(BaseModel):
    success: bool = True
    data: SupportedFormatsData
    message: str
    error: None = None


class IngestionData(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    article: ArticleResponse
    document_id: str
    chunk_count: int


class IngestionResponse(BaseModel):
    success: bool = True
    data: IngestionData
    message: str
    error: None = None
