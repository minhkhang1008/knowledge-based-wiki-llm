from sqlalchemy import Column, Integer, String, JSON, DateTime
from app.core.database import Base

class QALog(Base):
    __tablename__ = "qa_logs"
    id = Column(Integer,primary_key= True)
    question= Column(String,nullable= False)
    answer = Column(String,nullable= False)
    sources = Column(JSON) 
    created_at = Column(DateTime)
