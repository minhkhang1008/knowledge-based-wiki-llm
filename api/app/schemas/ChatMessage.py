from pydantic import BaseModel
from typing import Optional

class ChatMessage(BaseModel):
    role : str
    content : str