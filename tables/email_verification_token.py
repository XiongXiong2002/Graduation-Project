from database import Base

from sqlalchemy import Column,Integer,String,Boolean,ForeignKey,DateTime


from datetime import datetime, timezone


class EmailVerificationToken(Base):

    __tablename__ = "email_verification_tokens"

    id = Column(Integer, primary_key=True, index=True)

    # 属于哪个用户
    user_id = Column( Integer, ForeignKey("users.id"),nullable=False,index=True)

    # 随机 token
    token = Column(String(255),nullable=False,unique=True,index=True)

    # 是否已经使用
    used = Column(Boolean,nullable=False,default=False)

    # 过期时间
    expires_at = Column(DateTime, nullable=False)

    # 创建时间
    created_at = Column(DateTime,default=lambda: datetime.now(timezone.utc),nullable=False)