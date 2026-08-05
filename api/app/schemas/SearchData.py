from pydantic import BaseModel, Field
from typing import Optional, List
from app.schemas.SourceResponse import SourceResponse

class SearchData(BaseModel):
    results : Optional[List[SourceResponse]] = None