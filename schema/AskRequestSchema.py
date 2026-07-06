from pydantic import BaseModel, Field

class AskRequest(BaseModel):
    question : str = Field(min_length=5)