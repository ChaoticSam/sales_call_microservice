from sqlalchemy.orm import declarative_base
from sqlalchemy import Column, String, DateTime, Integer

Base = declarative_base()

class Call(Base):
    __tablename__ = "calls_db"

    call_id = Column(String, primary_key=True, index=True)
    agent_id = Column(String, nullable=False)
    customer_id = Column(String, nullable=False)
    language = Column(String, default="en")
    start_time = Column(DateTime, nullable=False)
    duration_seconds = Column(Integer)
    transcript = Column(String, nullable=False)
