from sqlalchemy import text
from database import engine, Base

def init_db():
    Base.metadata.create_all(bind=engine)

    sql_commands = [
        """
        ALTER TABLE users 
        ADD COLUMN IF NOT EXISTS is_email_verified BOOLEAN DEFAULT FALSE;
        """,
    ]

    with engine.begin() as conn:
        for sql in sql_commands:
            conn.execute(text(sql))