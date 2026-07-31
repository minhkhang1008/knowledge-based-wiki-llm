from pydantic import BaseModel, Field
from typing import Optional
from app.schemas.ChatMessage import ChatMessage

class AskRequest(BaseModel):
    question : str = Field(..., min_length=5)
    chat_history : list[ChatMessage] = Field(default_factory=list) # tạo list ms mỗi khi gọi