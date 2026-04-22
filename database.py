# database.py

import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker


# 1️⃣ 加载 .env 文件（读取环境变量）
load_dotenv()

# 2️⃣ 从 .env 中获取数据库连接地址
# 格式：postgresql://用户名:密码@主机:端口/数据库名
DATABASE_URL = os.getenv("DATABASE_URL")


# 3️⃣ 创建数据库连接引擎（Engine）
# 可以理解为：程序和数据库之间的“总连接通道”
engine = create_engine(
    DATABASE_URL
)


# 4️⃣ 创建 Session 工厂
# Session = 一次数据库操作的“会话”
# 每次增删改查都要通过 Session 来进行
SessionLocal = sessionmaker(
    autocommit=False,   # 不自动提交（需要手动 commit）
    autoflush=False,    # 不自动刷新（避免意外写入）
    bind=engine         # 绑定到刚刚创建的 engine
)


# 5️⃣ 创建 Base 类
# 所有数据库表（模型）都必须继承它
# 它负责：
# - 收集所有表结构
# - 后面统一创建表（create_all）
Base = declarative_base()


