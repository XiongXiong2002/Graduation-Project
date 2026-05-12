

from database import Base
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Boolean
from datetime import datetime, timezone




class MatchPool(Base):
    __tablename__ = "match_pool"

    id = Column(Integer, primary_key=True, index=True)

    # 只存导师
    mentor_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True, index=True)

    # 匹配条件快照
    status = Column(String(20), nullable=True, index=True)
    problem_type = Column(String(50), nullable=True, index=True)

    # 导师进入池子的时间
    joined_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)