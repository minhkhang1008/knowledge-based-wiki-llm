from asyncio import run
from pathlib import Path
from sqlalchemy import Column, Integer, String, JSON, DateTime
from datetime import datetime
from sqlalchemy.orm import declarative_base
from sqlalchemy.ext.asyncio import create_async_engine,async_sessionmaker
import os
baseURL = f"sqlite+aiosqlite:///{Path(__file__).with_name("database.db").resolve()}"
URLused = os.getenv("DATABASE_URL",baseURL)
engine = create_async_engine(URLused)
Base = declarative_base()
class QALog(Base):
    __tablename__ = "qa_logs"
    id = Column(Integer, primary_key=True)
    question= Column(String)
    answer = Column(String)
    created_at = Column(DateTime, default= datetime.now)
    source = Column(JSON)
async def build_database():
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all) 
Sessionmaker = async_sessionmaker(bind=engine)
async def log_qa_interaction(question: str, answer: str, source: list[dict]):
    async with Sessionmaker() as smaker:
        temporary = QALog(question=question, answer=answer, source =source)
        smaker.add(temporary)
        await smaker.commit()
if __name__ == "__main__" : 
   run(build_database())
