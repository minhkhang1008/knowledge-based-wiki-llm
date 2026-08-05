from app.core.database import Base
from sqlalchemy import Column,String,DateTime

class Article(Base):
    __tablename__ = "articles"
    id = Column(String, primary_key=True)
    document_id = Column(String, unique=True, nullable=False)
    title = Column(String, nullable= False)
    content = Column(String, nullable= False)
    source_file = Column(String, nullable= False)
    created_at = Column(DateTime)
    updated_at = Column(DateTime)
