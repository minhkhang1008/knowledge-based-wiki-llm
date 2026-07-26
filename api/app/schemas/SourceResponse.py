from pydantic import BaseModel
from typing import Optional, List, Dict, Any

class sourceResponse(BaseModel):
    text : str
    article_id : Optional[str] = None
    source_field : Optional[str] = None
    page_number: Optional[int] = None
    distance : Optional[float] = None