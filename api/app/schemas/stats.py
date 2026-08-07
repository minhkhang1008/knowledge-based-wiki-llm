from pydantic import BaseModel
from typing import Optional
from app.schemas.ErrorFormat import ErrorFormat

class StatsData(BaseModel):
    total_articles: int
    total_qa_logs: int
    total_indexed_chunks: int

class StatsResponse(BaseModel):
    success: bool
    data: StatsData | None = None
    message: str
    error: ErrorFormat | None = None
