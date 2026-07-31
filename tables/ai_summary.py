# standard library
from datetime import datetime, timezone

# third-party dependencies
from sqlalchemy import Column, DateTime, ForeignKey, Integer, Text

# database
from database import Base

# AI 聊天摘要表，用于保存每个用户的历史对话摘要
class AISummary(Base):
    __tablename__ = "ai_summaries"

    # 摘要记录的唯一 ID
    id = Column(Integer, primary_key=True, index=True)

    # 摘要所属的用户；每个用户只能拥有一条摘要记录
    user_id = Column(Integer,ForeignKey("users.id"),unique=True,nullable=False)

    # AI 根据历史聊天内容生成的摘要
    content = Column(Text, nullable=False, default="")

    # 摘要记录的创建时间，统一使用 UTC 时间
    created_at = Column(DateTime(timezone=True),default=lambda: datetime.now(timezone.utc),nullable=False)

    # 摘要最后更新时间；记录更新时自动刷新为当前 UTC 时间
    updated_at = Column(DateTime(timezone=True),default=lambda: datetime.now(timezone.utc),onupdate=lambda: datetime.now(timezone.utc),nullable=False)
