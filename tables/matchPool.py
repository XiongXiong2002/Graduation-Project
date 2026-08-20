

# standard library
from datetime import datetime, timezone

# third-party dependencies
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String

# database
from database import Base




class MatchPool(Base):
    __tablename__ = "match_pool"

    id = Column(Integer, primary_key=True, index=True)

    # 只存导师
    mentor_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True, index=True)

    # 匹配条件快照
    status = Column(String(20), nullable=True, index=True)
    problem_type = Column(String(50), nullable=True, index=True)

    institution = Column(String(100), nullable=True, index=True)
    location = Column(String(100), nullable=True, index=True)
    programme = Column(String(100), nullable=True)
    # Year of study the Mentor prefers to support.
    academic_level = Column(Integer, nullable=True, index=True)

    # 导师进入池子的时间
    joined_at = Column(DateTime(timezone=True),default=lambda: datetime.now(timezone.utc),nullable=False)
