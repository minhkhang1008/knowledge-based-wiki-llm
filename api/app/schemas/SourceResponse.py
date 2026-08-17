from pydantic import BaseModel, ConfigDict
from typing import Optional, List, Dict, Any

class SourceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    text : str
    article_id : Optional[str] = None
    source_file : Optional[str] = None
    page_number: Optional[int] = None
    distance : Optional[float] = None