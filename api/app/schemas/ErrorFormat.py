from pydantic import BaseModel
from typing import Optional

class ErrorFormat(BaseModel):
    code : str
    detail : str