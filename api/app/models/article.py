from datetime import datetime,timezone
from app.core.database import Base
from sqlalchemy import Column,String,DateTime,select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

class Article(Base):
    __tablename__ = "articles"
    id = Column(String, primary_key=True)
    document_id = Column(String, unique= True)
    title = Column(String, nullable= False)
    content = Column(String, nullable= False)
    source_file = Column(String, nullable= False)
    created_at = Column(DateTime, default= datetime.now(timezone.utc))
    updated_at = Column(DateTime)
