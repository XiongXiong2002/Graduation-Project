from database import Base 

from sqlalchemy import Column, Integer, String


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    password_hash = Column(String(128), nullable=False)
    # 用户角色：学生、导师、管理员等
    role = Column(String(20), nullable=False)  
    # 当前状态（考虑退学 / 已退学 / 学业困难）
    status = Column(String(20), nullable=True,default="not_student")
    # 主要问题类型（成绩 / 压力 / 人际 / 经济 / 其他）
    problem_type = Column(String(100), nullable=True)
    # 交流偏好（优先AI / 优先真人 / 都可以）
    preference = Column(String(20), nullable=True)
    

    