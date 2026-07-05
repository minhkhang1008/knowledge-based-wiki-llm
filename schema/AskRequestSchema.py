from pydantic import BaseModel, Field, ConfigDict

class AskRequest(BaseModel):
    question : str = Field(min_length=5)