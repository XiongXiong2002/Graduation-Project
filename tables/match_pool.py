from sqlalchemy import Column, Integer, DateTime, ForeignKey, String
from datetime import datetime, timezone
from database import Base

class MatchPool(Base):
    __tablename__ = "match_pool"

    id = Column(Integer, primary_key=True, index=True)

    # 可被匹配的接收者ID（一般是 mentor）
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True, index=True)

    # 加入匹配池的时间
    joined_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # 最后一次活跃时间
    last_heartbeat = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    #是否已经在进行咨询
    is_matched = Column(bool, default=False, nullable=False)

    # 接受咨询的状态（考虑退学 / 已退学 / 学业困难）
    status = Column(String(20), nullable=True,default="not_student")

    # 接受咨询问题类型（成绩 / 压力 / 人际 / 经济 / 其他）
    problem_type = Column(String(100), nullable=True)