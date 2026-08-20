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
        """
        -- Student: current year; Mentor: year they prefer to support.
        ALTER TABLE users
        ADD COLUMN IF NOT EXISTS academic_level INTEGER;
        """,
        """
        -- Cache the year the Mentor prefers to support while they are available.
        ALTER TABLE match_pool
        ADD COLUMN IF NOT EXISTS academic_level INTEGER;
        """,
        """
        -- 区分注册邮箱验证和 Mentor 学校邮箱验证
        ALTER TABLE email_verification_tokens
        ADD COLUMN IF NOT EXISTS purpose VARCHAR(20) DEFAULT 'register' NOT NULL;
        """,
        """
        -- 将旧 Mentor Boolean 状态一次性迁移为三状态字符串，然后删除旧字段。
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'users' AND column_name = 'is_mentor_verified'
            ) AND NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'users' AND column_name = 'mentor_verify_status'
            ) THEN
                ALTER TABLE users
                ADD COLUMN mentor_verify_status VARCHAR(20) DEFAULT 'disapprove';

                UPDATE users
                SET mentor_verify_status = CASE
                    WHEN is_mentor_verified THEN 'approve'
                    ELSE 'disapprove'
                END;

                ALTER TABLE users
                ALTER COLUMN mentor_verify_status SET NOT NULL;

                ALTER TABLE users DROP COLUMN is_mentor_verified;
            END IF;
        END $$;
        """,
    ]

    with engine.begin() as conn:
        for sql in sql_commands:
            conn.execute(text(sql))
