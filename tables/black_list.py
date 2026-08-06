# third-party dependencies
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String

# database
from database import Base


class BlackList(Base):

    __tablename__ = "black_list"
    id = Column(Integer, primary_key=True, index=True)

    # 属于哪个用户
    blocker_id = Column( Integer, ForeignKey("users.id"),nullable=False,index=True)

    # 被拉黑的用户
    blocked_id = Column( Integer, ForeignKey("users.id"),nullable=False,index=True)

    # 创建时间
    created_at = Column( DateTime(timezone=True), nullable=False)

    #被拉黑原因
    reason = Column(String(255),nullable=True)
