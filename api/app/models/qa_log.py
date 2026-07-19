from sqlalchemy import Column, Integer, String, JSON, DateTime
from datetime import datetime
from app.core.database import Base, get_db
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends
class QALog(Base):
    __tablename__ = "qa_logs"
    id = Column(Integer, primary_key=True)
    question= Column(String)
    answer = Column(String)
    created_at = Column(DateTime, default= datetime.now)
    source = Column(JSON) 
async def log_qa_interaction(session: AsyncSession, question: str, answer: str, source: list[dict]):     
    temporary = QALog(question=question, answer=answer, source =source)
    session.add(temporary)
    await session.commit()
