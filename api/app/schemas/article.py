from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime  import datetime

class ArticleCreate(BaseModel):
    document_id : str
    title : str
    content : str # cái này chưa biết để gì hết
    source_file : str

class ArticleUpdate(BaseModel):
    title : str
    content : str
    source_file : str

class ArticleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True) # giup doc dc bang . va []

    id : str
    document_id : str
    title : str
    content : str
    source_file : str
    created_at : datetime
    updated_at : datetime