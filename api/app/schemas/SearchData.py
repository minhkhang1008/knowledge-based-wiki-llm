from pydantic import BaseModel, Field
from typing import Optional

class searchData(BaseModel):
    query : str = Field(..., min_length=2)