from datetime import datetime
from asyncio import run
from pathlib import Path
from sqlalchemy import Column, Integer, String, JSON, DateTime, func, select
from sqlalchemy.orm import declarative_base
from sqlalchemy.ext.asyncio import create_async_engine,async_sessionmaker
databaseURL = Path(__file__).with_name("database.db").resolve()
engine = create_async_engine(f"sqlite+aiosqlite:///{databaseURL}")
Base = declarative_base()
class QALog(Base):
    __tablename__ = "qa_logs"
    Question_id = Column(Integer, primary_key=True)
    statement = Column(String)
    respond = Column(String)
    created_at = Column(DateTime, default=datetime.now)
    source = Column(JSON)
Sessionmaker = async_sessionmaker(bind=engine)
maker = Sessionmaker()
async def build_database():
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all) 
async def count_questions() -> int:
    return await maker.scalar(select(func.count()).select_from(QALog)) or 0
async def add_informations( _statement: str, _respond: str, _source: list[dict]):
    temporary = QALog(Question_id = await count_questions(), statement=_statement, respond=_respond, source=_source)
    maker.add(temporary)
    await maker.commit()
if __name__ == "__main__" : 
   run(build_database())