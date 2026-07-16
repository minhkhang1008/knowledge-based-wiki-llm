from datetime import datetime
from sqlalchemy.ext.asyncio import async_sessionmaker,create_async_engine
from sqlalchemy import Column,String,DateTime,select
from sqlalchemy.orm import declarative_base
from asyncio import run
import os 
from typing import Optional
from pathlib import Path
basedURL = f"sqlite+aiosqlite:///{Path(__file__).with_name('database.db').resolve()}"
databaseURL = os.getenv("DATABASE_URL",basedURL)
engine = create_async_engine(databaseURL)
Base = declarative_base()
AsyncSessionLocal = async_sessionmaker(bind = engine,expire_on_commit= False)
class Article(Base):
    __tablename__ = "articles"
    id = Column(String, primary_key=True)
    title = Column(String, nullable=False)
    content = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.now)
async def build_base():
    async with engine.begin() as cnn:
       await cnn.run_sync(Base.metadata.create_all)
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
if __name__ == "__main__":
    run(build_base())
