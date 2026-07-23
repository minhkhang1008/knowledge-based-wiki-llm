from sqlalchemy import Column, Integer, String, JSON, DateTime
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import Base

class QALog(Base):
    __tablename__ = "qa_logs"
    id = Column(Integer, primary_key=True)
    question= Column(String, nullable= False)
    answer = Column(String, nullable= False)
    sources = Column(JSON) 
    created_at = Column(DateTime, default= datetime.now)


async def log_qa_interaction(session: AsyncSession, question: str, answer: str, source: list[dict]):     
    temporary = QALog(question=question, answer=answer, source =source)
    session.add(temporary)
    await session.commit()
