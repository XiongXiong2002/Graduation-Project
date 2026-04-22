from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from datetime import datetime, timezone
from database import Base

class Message(Base):
    __tablename__ = "messages"

    # 消息唯一标识
    id = Column(Integer, primary_key=True, index=True)

    # 所属对话ID
    session_id = Column(Integer, ForeignKey("sessions.id"), nullable=False, index=True)

    # 发送方（user / ai / mentor）
    sender_type= Column(String(20), nullable=False)

    sender_id = Column(Integer, ForeignKey("users.id"), nullable=True) # 发送者ID，用户消息为用户ID，AI消息为null

    # 消息内容
    content = Column(String, nullable=False)

    # 发送时间（UTC）
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)