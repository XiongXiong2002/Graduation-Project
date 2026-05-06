from datetime import datetime, timedelta, timezone
from fastapi.security import OAuth2PasswordBearer
from jose import jwt
from jose import jwt, JWTError
from fastapi import Depends, HTTPException

from database import SessionLocal
from tables.user import User

# 🔐 用来签名 token 的密钥
SECRET_KEY = "2273047bb4c10f8386e9fc1db1b42e474710870c250c79bb24e99d708aee1c67"

# 🔐 使用的加密算法（固定写 HS256 就行）
ALGORITHM = "HS256"

# ⏰ token 有效期（这里是 24 小时）
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24

# ✅ 从请求头里自动提取 token
# 它会读取：
# Authorization: Bearer xxxxx
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/user/login")

def create_access_token(data: dict):

    # ✅ 复制一份数据，避免修改原始 data
    to_encode = data.copy()
        # 防止忘记 sub
    if "sub" not in to_encode:
        raise ValueError("Token data must contain 'sub'")

    # ⏰ 计算 token 过期时间（当前时间 + 有效期）
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=ACCESS_TOKEN_EXPIRE_MINUTES
    )

    # ✅ 把过期时间加进 token 数据中
    # exp = expire（JWT 标准字段，表示过期时间）
    to_encode.update({
        "exp": expire
    })

    # 🔑 核心步骤：生成 token
    # 做了三件事：
    # 1. 把数据转成字符串
    # 2. 用 SECRET_KEY 进行签名（防伪）
    # 3. 生成一串 token
    token = jwt.encode(
        to_encode,      # 数据（包含 sub + exp）
        SECRET_KEY,     # 密钥（用来签名）
        algorithm=ALGORITHM  # 算法
    )

    # ✅ 返回 token（一个字符串）
    return token




def verify_token(token: str):
    """
    输入: token 字符串
    输出: user_id（如果合法）
    """

    try:
        # 1️⃣ 解码 token（同时验证签名 + 是否过期）
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM]
        )

        # 2️⃣ 取出 user_id（我们之前放在 sub 里）
        user_id = payload.get("sub")

        # 3️⃣ 如果没有 sub，说明 token 不合法
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")

        # 4️⃣ 返回 user_id
        return int(user_id)

    except JWTError:
        # token 过期 / 被篡改 / 格式错误都会进这里
        raise HTTPException(status_code=401, detail="Invalid token")
    

def get_current_user(token: str = Depends(oauth2_scheme)):
    """
    FastAPI 依赖函数：
    从请求头拿 token → 验证 token → 查数据库 → 返回当前用户
    """

    user_id = verify_token(token)

    db = SessionLocal()

    try:
        user = db.query(User).filter(User.id == user_id).first()

        if not user:
            raise HTTPException(status_code=401, detail="User not found")

        return user

    finally:
        db.close()