from datetime import datetime
from app.core.database import Base
from sqlalchemy import Column,String,DateTime,select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

class Article(Base):
    __tablename__ = "articles"
    id = Column(String, primary_key=True)
    document_id = Column(String)
    title = Column(String, nullable=False)
    content = Column(String, nullable=False)
    source_file = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime)
    
async def get_all_articles(session: AsyncSession,skip: int, limit: int, search: Optional[str] = None):
    stmt = select(Article).offset(skip).limit(limit)
    if search:
        stmt = stmt.where(Article.title.like(f"%{search}%"))
    result = await session.execute(stmt)
    return result.scalars().all()
async def get_article_by_id(session: AsyncSession, article_id: str):
    stmt = select(Article).where(Article.id == article_id)
    result = await session.execute(stmt)
    return  result.scalar_one_or_none()
