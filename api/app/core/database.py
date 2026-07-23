from sqlalchemy.orm import declarative_base
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker,AsyncSession
import os 
DATABASE_URL = os.getenv("DATABASE.URL","sqlite+aiosqlite:///./knowledge_base.db")
engine  = create_async_engine(DATABASE_URL, echo=True)
Base = declarative_base()
AsyncSessionLocal = async_sessionmaker(bind = engine, class_= AsyncSession, expire_on_commit= False)

async def init_db():
    from api.app.models.qa_log import QAlog
    from api.app.models.article import Article
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
