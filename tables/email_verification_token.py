# standard library
from datetime import datetime, timezone

# third-party dependencies
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String

# database
from database import Base


class EmailVerificationToken(Base):

    __tablename__ = "email_verification_tokens"

    id = Column(Integer, primary_key=True, index=True)

    # 属于哪个用户
    user_id = Column( Integer, ForeignKey("users.id"),nullable=False,index=True)

    # 随机 token
    token = Column(String(255),nullable=False,unique=True,index=True)

    # purpose 区分注册邮箱验证 register 和学校邮箱验证 mentor。
    purpose = Column(String(20), nullable=False, default="register")

    # 是否已经使用
    used = Column(Boolean,nullable=False,default=False)

    # 过期时间
    expires_at = Column(DateTime(timezone=True), nullable=False)
    # 创建时间
    created_at = Column( DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),nullable=False)
