from sqlalchemy.orm import declarative_base
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker,AsyncSession

engine  = create_async_engine("sqlite+aiosqlite:///./knowledge_base.db", echo=True)
Base = declarative_base()
AsyncSessionLocal = async_sessionmaker(bind = engine, class_= AsyncSession, expire_on_commit= False)
async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
async def get_db():
    async with AsyncSessionLocal() as smaker:
        try:
            yield smaker
        finally:
            await smaker.commit()
            await smaker.close()
