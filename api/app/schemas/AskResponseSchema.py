from pydantic import BaseModel
from typing import Optional, List, Dict, Any

class dataResponse(BaseModel):
    answer: str
    sources: List[Dict[str, Any]]

class AskResponse(BaseModel):
    success: bool
    data: dataResponse
    message: str
    error: Optional[str] = None