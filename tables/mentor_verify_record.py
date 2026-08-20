# database
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Integer, String

from database import Base

class MentorVerifyRecord(Base):
    __tablename__ = "mentor_verify_records"
    
    id = Column(Integer, primary_key=True, index=True)

    # 验证时间
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # 验证的mentor用户ID
    mentor_id = Column(Integer, nullable=False, index=True)

    # 验证学校
    institution = Column(String(100), nullable=True)


    