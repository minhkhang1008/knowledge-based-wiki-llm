from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from app.schemas.ErrorFormat import ErrorFormat

class DataResponse(BaseModel):
    answer: str
    sources: List[Dict[str, Any]]
    no_answer_reason : Optional[str] = None

class AskResponse(BaseModel):
    success: bool
    data: Optional[DataResponse] = None
    message: str
    error: Optional[ErrorFormat] = None