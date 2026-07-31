# standard library
from datetime import datetime, timezone

# third-party dependencies
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String

# database
from database import Base


class Session(Base):
    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True, index=True)

    # 提出用户id
    req_user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    # 接受用户id （null 表示AI）
    acc_user_id = Column(Integer, ForeignKey("users.id"), nullable=True , index=True )

    # 状态：open / closed
    state = Column(String(10), nullable=False, default="open")

    # 是否是ai
    match_type = Column(String(10),nullable=False ,default= "mentor")

    # 创建时间
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
