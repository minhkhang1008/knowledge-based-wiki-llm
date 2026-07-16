from datetime import datetime
from core.database import Base, AsyncSessionLocal
from sqlalchemy import Column,String,DateTime,select
from typing import Optional
class Article(Base):
    __tablename__ = "articles"
    id = Column(String, primary_key=True)
    title = Column(String, nullable=False)
    content = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.now)
async def get_all_articles(skip: int, limit: int, search: Optional[str] = None):
    async with AsyncSessionLocal() as smaker:
        stmt = select(Article).offset(skip).limit(limit)
        if search:
            stmt = stmt.where(Article.title.like(f"%{search}%"))
        result = await smaker.execute(stmt)
        return result.scalars().all()
async def get_article_by_id(article_id: str):
    async with AsyncSessionLocal() as smaker:
        stmt = select(Article).where(Article.id == article_id)
        result = await smaker.execute(stmt)
        return  result.scalar_one_or_none()
