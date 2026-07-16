from pydantic import BaseModel
from typing import Optional

class dataResponse(BaseModel):
    answer : str
    sources : list[str]

class AskResponse(BaseModel):
    success : bool
    data : dataResponse
    message : str
    error : Optional[str] = None