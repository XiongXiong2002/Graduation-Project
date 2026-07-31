# database
from database import Base

# third-party dependencies
from sqlalchemy import Boolean, Column, Integer, String


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

    # 邮箱是否验证
    is_email_verified = Column(Boolean, nullable=False, default=False)
    # 学校信息
    institution = Column(String(100), nullable=True)
    # 专业信息
    programme = Column(String(100), nullable=True)

    # 当前地区
    location = Column(String(100), nullable=True)

    # 是否登录
    logged_in_id = Column(Integer, nullable=False, default=0)

    # 照片路径（可指向 img 目录中的图片）
    # 只保存用户选择的合法头像路径，图片文件本身保存在 img 目录。
    photo = Column(String(255), nullable=True)

    # 个人格言
    # 个人格言由注册或修改资料接口写入，当前最多允许 200 个字符。
    motto = Column(String(255), nullable=True)

