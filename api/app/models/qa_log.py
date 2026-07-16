from sqlalchemy import Column, Integer, String, JSON, DateTime
from datetime import datetime
from core.database import Base, AsyncSessionLocal
class QALog(Base):
    __tablename__ = "qa_logs"
    id = Column(Integer, primary_key=True)
    question= Column(String)
    answer = Column(String)
    created_at = Column(DateTime, default= datetime.now)
    source = Column(JSON) 
async def log_qa_interaction(question: str, answer: str, source: list[dict]):
    async with AsyncSessionLocal() as smaker:
        temporary = QALog(question=question, answer=answer, source =source)
        smaker.add(temporary)
        await smaker.commit()
