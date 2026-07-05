from pydantic import BaseModel, Field, ConfigDict

class AskResponse(BaseModel):
    answer : str

    sources : list[dict]