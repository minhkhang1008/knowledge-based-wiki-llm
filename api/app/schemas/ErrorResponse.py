from pydantic import BaseModel
from typing import Optional
from app.schemas.ErrorFormat import ErrorFormat

class ErrorResponse(BaseModel):
    success : bool
    data : None
    message : str
    error : ErrorFormat