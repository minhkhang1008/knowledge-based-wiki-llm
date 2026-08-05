from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from app.schemas.ErrorFormat import ErrorFormat
from app.schemas.SearchData import SearchData

class SearchResponse(BaseModel):
    success : bool
    data : Optional[SearchData] = None
    message : str
    error : Optional[ErrorFormat] = None

