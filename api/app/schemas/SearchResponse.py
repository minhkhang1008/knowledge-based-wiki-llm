from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from app.schemas.ErrorFormat import errorFormat
from app.schemas.SourceResponse import sourceResponse

class searchResponse(BaseModel):
    success : bool
    data : Optional[List[sourceResponse]] = None
    message : str
    error : Optional[errorFormat] = None

