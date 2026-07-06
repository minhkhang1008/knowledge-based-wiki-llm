from pydantic import BaseModel

class AskSource(BaseModel):
    id : str
    title : str
    url : str

class AskResponse(BaseModel):
    answer : str