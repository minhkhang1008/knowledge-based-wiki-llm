from pydantic import BaseModel
from typing import Optional

class errorFormat(BaseModel):
    code : str
    detail : str