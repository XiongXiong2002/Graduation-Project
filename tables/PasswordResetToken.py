# third-party dependencies
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String

# database
from database import Base
# 用户的密码重设 token 表
class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"

    id = Column(Integer, primary_key=True, index=True)

    # 这个 token 属于哪个用户
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    # 重设密码用的一次性 token
    token = Column(String, unique=True, nullable=False, index=True)

    # 过期时间，建议 15 分钟或 1 小时
    expires_at = Column(DateTime(timezone=True), nullable=False)

    # 是否已经使用过
    used = Column(Boolean, default=False, nullable=False)
