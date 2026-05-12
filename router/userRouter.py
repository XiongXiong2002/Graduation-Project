from database import SessionLocal
from schames.login import loginRequest
from schames.personalInfo import personalInfoRequest
from schames.register import registerRequest
from tables.user import User
from tables.email_verification_token import EmailVerificationToken
from auth import create_access_token, get_current_user, verify_token
from tools.password_hashed import hash_password, verify_legal_password, verify_password
from fastapi import APIRouter, Depends
from tools.token_create import generate_token
from datetime import datetime, timedelta, timezone
from service.email_service import send_email


app = APIRouter()

@app.post("/user/login")
def login(user: loginRequest):
    db = SessionLocal()
    try:
        matched_user= db.query(User).filter(User.email == user.email).first()  
        if not matched_user:
            return {"msg": "invalid email or password"}
        if not matched_user.is_email_verified:
            return {"msg": "email not verified",
                    "email": matched_user.email 
                    }
        if (verify_password(user.password, matched_user.password_hash)):
           # ✅ 登录成功后，用当前用户 id 生成 token
            access_token = create_access_token({
                "sub": str(matched_user.id)
            })

            return {
                "msg": "login successful",

                # ✅ 返回 token 给前端
                "access_token": access_token,
                "token_type": "bearer",

                # ✅ 原来的用户信息照常返回
                "user_info": {
                    "id": matched_user.id,
                    "username": matched_user.username,
                    "email": matched_user.email,
                    "role": matched_user.role
                }
            }

        else:
            return {"msg": "invalid email or password"}

    finally:
        db.close()

@app.post("/user/register")
def register(user: registerRequest):
    db = SessionLocal()
    try:
        existing_user = db.query(User).filter(User.email == user.email).first()
        if existing_user:
            return {"msg": "email already registered"}
        
        if not verify_legal_password(user.password) :
            return {"msg": "Password requirements: 8–20 characters, must include uppercase letters, lowercase letters, and special characters"}

        new_user = User(
            username=user.username,
            email=user.email,
            password_hash=hash_password(user.password),
            role=user.role,
            status=user.status,
            problem_type=user.problem_type,
            preference=user.preference
        )
        db.add(new_user)

        db.flush()
        token = generate_token()

        verification = EmailVerificationToken(
            user_id=new_user.id,
            token=token,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=24)
        )
        db.add(verification)

        db.commit()
        # TODO: 发送验证邮件，包含 verification.token
        send_email(
            to_email=new_user.email,
            subject="Please verify your email",
            body=f"""
                Please verify your email by clicking the link below:

                    {http://localhost:8000/user/verify_email?token={token}}

                This link will expire in 24 hours.""")
    finally:
        db.close()

@app.post("/user/update_profile")
def update_profile(
    data: personalInfoRequest,
    current_user: User = Depends(get_current_user)
):
    db = SessionLocal()

    try:
        user = db.query(User).filter(User.id == current_user.id).first()

        if not user:
            return {"msg": "user not found"}

        if data.username is not None:
            user.username = data.username

        if data.status is not None:
            user.status = data.status

        if data.problem_type is not None:
            user.problem_type = data.problem_type

        if data.preference is not None:
            user.preference = data.preference

        db.commit()

        return {
            "msg": "profile updated"
        }

    finally:
        db.close()



@app.post("/user/update_password")
def update_password(user_id: int, user: registerRequest):pass



# 邮箱验证接口
# 用户点击邮件中的验证链接后会访问这里

@app.get("/user/verify_email")
def verify_email(token: str):    

    # 创建数据库连接
    db = SessionLocal()

    try:

        # 根据 token 查找验证记录
        record = db.query(EmailVerificationToken).filter(
            EmailVerificationToken.token == token
        ).first()

        # token 不存在
        if not record:
            return {"msg": "invalid token"}

        # token 已经被使用过
        if record.used:
            return {"msg": "token already used"}

        # 获取当前 UTC 时间
        # 这里使用 utcnow() 避免 naive/aware datetime 比较报错
        now = datetime.utcnow()

        # 检查 token 是否过期
        if record.expires_at < now:
            return {"msg": "token expired"}

        # 根据 token 记录中的 user_id 查找用户
        user = db.query(User).filter(
            User.id == record.user_id
        ).first()

        # 用户不存在
        if not user:
            return {"msg": "user not found"}

        # 设置用户邮箱已验证
        user.is_email_verified = True

        # 设置 token 已使用
        # 防止重复点击
        record.used = True

        # 提交数据库修改
        db.commit()

        # 返回成功消息
        return {"msg": "email verified successfully"}

    finally:

        # 无论成功还是失败
        # 最后都关闭数据库连接
        db.close()


# 查询邮箱验证状态
@app.get("/user/check_verification")
def check_verification(email: str):

    # 创建数据库连接
    db = SessionLocal()

    try:

        # 查找用户
        user = db.query(User).filter(
            User.email == email
        ).first()

        # 用户不存在
        if not user:
            return {
                "verified": False
            }

        # 返回邮箱验证状态
        return {
            "verified": user.is_email_verified
        }

    finally:

        # 关闭数据库连接
        db.close()

@app.post("/user/resend_verification_email")
def resend_verification_email(email: str):
    db = SessionLocal()

    try:
        user = db.query(User).filter(User.email == email).first()

        if not user:
            return {"msg": "if this email exists, a verification email has been sent"}

        if user.is_email_verified:
            return {"msg": "email already verified"}

        token = generate_token()

        verification = EmailVerificationToken(
            user_id=user.id,
            token=token,
            expires_at=datetime.utcnow() + timedelta(hours=24)
        )

        db.add(verification)
        db.commit()

        verification_link = f"http://localhost:8000/user/verify_email?token={token}"

        send_email(
            to_email=user.email,
            subject="Please verify your email",
            body=f"""
Please verify your email by clicking the link below:

{verification_link}

This link will expire in 24 hours.
"""
        )

        return {"msg": "verification email sent"}

    finally:
        db.close()