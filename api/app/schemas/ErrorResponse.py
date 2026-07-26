from pydantic import BaseModel
from typing import Optional
from app.schemas.ErrorFormat import errorFormat

class errorResponse(BaseModel):
    success : bool
    data : None
    message : str
    error : errorFormat