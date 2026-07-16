from sqlalchemy import Column, Integer, String, JSON, DateTime
from datetime import datetime
from core.database import Base, get_db
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends
class QALog(Base):
    __tablename__ = "qa_logs"
    id = Column(Integer, primary_key=True)
    question= Column(String)
    answer = Column(String)
    created_at = Column(DateTime, default= datetime.now)
    source = Column(JSON) 
async def log_qa_interaction(question: str, answer: str, source: list[dict], smaker : AsyncSession = Depends(get_db)):
    temporary = QALog(question=question, answer=answer, source =source)
    smaker.add(temporary)
    await smaker.commit()
