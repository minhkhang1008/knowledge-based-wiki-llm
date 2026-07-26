from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from app.schemas.ErrorFormat import errorFormat

class dataResponse(BaseModel):
    answer: str
    sources: List[Dict[str, Any]]
    no_answer_reason : str

class AskResponse(BaseModel):
    success: bool
    data: Optional[dataResponse] = None
    message: str
    error: Optional[errorFormat] = None