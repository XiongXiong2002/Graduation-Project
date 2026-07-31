# third-party dependencies
from sqlalchemy import text

# database
from database import Base, engine

def init_db():
    Base.metadata.create_all(bind=engine)

    sql_commands = [
        """
        ALTER TABLE users 
        ADD COLUMN IF NOT EXISTS is_email_verified BOOLEAN DEFAULT FALSE;
        """,
        """
        -- 为已有 users 表补充头像路径字段。
        ALTER TABLE users
        ADD COLUMN IF NOT EXISTS photo VARCHAR(255);
        """,
        """
        -- 为已有 users 表补充个人格言字段。
        ALTER TABLE users
        ADD COLUMN IF NOT EXISTS motto VARCHAR(255);
        """,
    ]

    with engine.begin() as conn:
        for sql in sql_commands:
            conn.execute(text(sql))
