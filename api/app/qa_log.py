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
    id = Column(Integer, primary_key=True)
    question= Column(String)
    answer = Column(String)
    created_at = Column(DateTime)
    source = Column(JSON)
Sessionmaker = async_sessionmaker(bind=engine)
maker = Sessionmaker()
async def build_database():
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all) 

async def add_informations(_id: int, _question: str, _answer: str, _source: list[dict]):
    temporary = QALog(id = _id, question=_question, answer=_answer, source =_source)
    maker.add(temporary)
    await maker.commit()
if __name__ == "__main__" : 
   run(build_database())