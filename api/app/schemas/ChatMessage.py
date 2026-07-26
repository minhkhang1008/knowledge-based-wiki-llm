from pydantic import BaseModel
from typing import Optional

class chatMessage(BaseModel):
    role : str
    content : str