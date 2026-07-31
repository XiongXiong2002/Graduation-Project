# standard library
from datetime import datetime, timedelta, timezone

# third-party dependencies
from fastapi import APIRouter

# database
from database import SessionLocal

# request schema
from schames.login import loginRequest
from schames.register import registerRequest
from schames.reset import ResetPasswordRequest
from schames.check_reset import CheckResetTokenRequest

# database tables
from tables.user import User
from tables.email_verification_token import EmailVerificationToken
from tables.PasswordResetToken import PasswordResetToken
from tables.ai_summary import AISummary


# auth
from auth import create_access_token

# password tools
from tools.password_hashed import (
    hash_password,
    verify_legal_password,
    verify_password
)
from tools.get_file_data import (
    load_city_names,
    load_university_names,
    VALID_PROBLEM_TYPES,
    VALID_STATUSES,
    VALID_IMG,
)

# token generator
from tools.token_create import generate_token

# email service
from service.email_service import send_email

# 创建 router
app = APIRouter()

VALID_CITIES = load_city_names()
VALID_UNIVERSITIES = load_university_names()


# =========================
# 用户登录
# =========================
@app.post("/user/login")
def login(user: loginRequest):

    db = SessionLocal()

    try:

        # 根据邮箱查找用户
        matched_user = db.query(User).filter(
            User.email == user.email
        ).first()

        # 用户不存在
        if not matched_user:

            return {
                "msg": "invalid email or password"
            }

        # 邮箱未验证
        if not matched_user.is_email_verified:

            return {
                "msg": "email not verified",
                "email": matched_user.email
            }

        # 密码正确
        if verify_password(user.password,matched_user.password_hash):
            matched_user.logged_in_id = matched_user.logged_in_id+1

            # 保存到数据库
            db.commit()
            db.refresh(matched_user)
            # 生成 JWT token
            access_token = create_access_token({"sub": str(matched_user.id),"logged_id" :matched_user.logged_in_id})


            return {

                "msg": "login successful",

                # JWT token
                "access_token": access_token,

                "token_type": "bearer",

                # 用户信息
                "user_info": {
                    "id": matched_user.id,
                    "username": matched_user.username,
                    "email": matched_user.email,
                    "role": matched_user.role,
                    "status": matched_user.status,
                    "problem_type": matched_user.problem_type,
                    "institution": matched_user.institution,
                    "programme": matched_user.programme,
                    "location": matched_user.location,
                    # 登录后将头像路径和格言交给前端保存到 user_info。
                    "img": matched_user.photo,
                    "motto": matched_user.motto
                }
            
            }
            
        # 密码错误
        else:

            return {
                "msg": "invalid email or password"
            }

    finally:

        db.close()


# =========================
# 用户注册
# =========================
@app.post("/user/register")
def register(user: registerRequest):

    db = SessionLocal()

    try:

        # 检查邮箱是否已存在
        existing_user = db.query(User).filter(
            User.email == user.email
        ).first()

        if existing_user:

            return {
                "msg": "email already registered"
            }

        status = user.status
        problem_type = user.problem_type

        if not user.username.strip():

            return {
                "msg": "invalid username"
            }

        if user.role not in {"student", "mentor"}:

            return {
                "msg": "invalid role"
            }

        if status is not None and status not in VALID_STATUSES:

            return {
                "msg": "invalid status"
            }

        if problem_type is not None and problem_type not in VALID_PROBLEM_TYPES:

            return {
                "msg": "invalid problem type"
            }

        if user.institution not in VALID_UNIVERSITIES:

            return {
                "msg": "invalid institution"
            }

        if user.location not in VALID_CITIES:

            return {
                "msg": "invalid location"
            }

        if not user.programme.strip():

            return {
                "msg": "invalid programme"
            }

        # 注册提交的头像必须来自后端提供的合法头像白名单。
        if user.img not in VALID_IMG:
            return {
                "msg": "invalid img"
            }

        # 沿用当前审核规则：个人格言最多 200 个字符。
        if len(user.motto) > 200:
            return {
                "msg": "invalid motto"
            }

        # 检查密码是否合法
        if not verify_legal_password(user.password):

            return {
                "msg":
                "Password requirements: 8–20 characters, must include uppercase letters, lowercase letters, and special characters"
            }

        # 创建用户
        new_user = User(
            username=user.username.strip(),
            email=user.email,
            password_hash=hash_password(user.password),
            role=user.role,
            status=status,
            problem_type=problem_type,
            institution=user.institution,
            programme=user.programme.strip(),
            location=user.location,
            # 数据库保存头像路径，不保存图片二进制内容。
            photo=user.img,
            motto=user.motto.strip()
        )

        db.add(new_user)

        # 提前获取 user id
        db.flush()

        # 生成邮箱验证 token
        token = generate_token()

        # 创建邮箱验证记录
        verification = EmailVerificationToken(
            user_id=new_user.id,
            token=token,
            expires_at=datetime.now(timezone.utc)
            + timedelta(hours=24)
        )

        db.add(verification)

        

        # 发送邮箱验证邮件
        send_email(
            to_email=new_user.email,

            subject="Please verify your email",

            body=f""" Please verify your email by clicking the link below:
    
                    http://localhost:5173/user/verify_register_email?token={token}

                    This link will expire in 24 hours.
                """
        )


        summary_for_user = AISummary(
            user_id = new_user.id
        )

        db.add(summary_for_user)

        db.commit()

        return {
            "msg":
            "register successful, please verify your email"
        }

    finally:

        db.close()


# =========================
# 请求重设密码邮件
# =========================
@app.post("/user/request_password_reset")
def request_password_reset(email: str):

    db = SessionLocal()

    try:

        # 查找用户
        user = db.query(User).filter( User.email == email).first()

        # 无论用户是否存在
        # 都返回相同消息
        # 防止邮箱探测
        if not user:

            return {
                "msg":
                "if this email exists, a reset link has been sent"
            }

        # 作废旧 reset token
        db.query(PasswordResetToken).filter( PasswordResetToken.user_id == user.id,PasswordResetToken.used == False).update({"used": True})

        # 生成新 token
        token = generate_token()

        # 创建 reset token
        reset_token = PasswordResetToken(
            user_id=user.id,
            token=token,
            expires_at=datetime.now(timezone.utc)
            + timedelta(minutes=30)
        )

        db.add(reset_token)

        db.commit()

        # reset password 页面链接
        reset_link = (
            f"http://localhost:5173/reset_password?token={token}"
        )

        # 发送邮件
        send_email(
            to_email=user.email,

            subject="Reset your password",

            body=f"""
Please reset your password by clicking the link below:

{reset_link}

This link will expire in 30 minutes.
"""
        )

        return {
            "msg":
            "if this email exists, a reset link has been sent"
        }

    finally:

        db.close()


@app.post("/user/check_reset_token")
def check_reset_token(req: CheckResetTokenRequest):
    db = SessionLocal()

    try:

        # 查找 token
        record = db.query(PasswordResetToken).filter( PasswordResetToken.token == req.token,PasswordResetToken.used == False).first()

        # token 不存在或已使用
        if not record:

            return {
                "valid": False,
                "msg": "invalid or used token"
            }

        # 当前 UTC 时间
        now = datetime.now(timezone.utc)

        # token 过期
        if record.expires_at < now:

            return {
                "valid": False,
                "msg": "token expired"
            }

        return {
            "valid": True,
            "msg": "token is valid"
        }

    finally:

        db.close()

# 检查重置密码 token 是否有效
# 用于 Reset Password 页面加载时验证链接合法性
@app.post("/user/reset_password")
def reset_password(req: ResetPasswordRequest):  
    db = SessionLocal()

    try:

        # 查找 token
        record = db.query(PasswordResetToken).filter( PasswordResetToken.token == req.token,PasswordResetToken.used == False).first()

        # token 不存在或已使用
        if not record:

            return {
                "msg": "invalid or used token"
            }

        # 当前 UTC 时间
        now = datetime.now(timezone.utc)

        # token 过期
        if record.expires_at < now:

            return {
                "msg": "token expired"
            }

        # 查找用户
        user = db.query(User).filter(
            User.id == record.user_id
        ).first()

        # 用户不存在
        if not user:

            return {
                "msg": "user not found"
            }

        # 检查新密码是否合法
        if not verify_legal_password(req.new_password):

            return {
                "msg":
                "Password requirements: 8–20 characters, must include uppercase letters, lowercase letters, and special characters"
            }

        # 更新密码
        user.password_hash = hash_password(req.new_password)

        # 设置 token 已使用
        record.used = True

        db.commit()

        return {
            "msg": "password reset successful"
        }

    finally:

        db.close()


# =========================
# 注册邮箱验证接口
# =========================
@app.get("/user/verify_register_email")
def verify_email(token: str):

    db = SessionLocal()

    try:

        # 查找 token
        record = db.query(
            EmailVerificationToken
        ).filter(
            EmailVerificationToken.token == token
        ).first()

        # token 不存在
        if not record:

            return {
                "msg": "invalid token",
                "resend": False 
            }

        # token 已使用
        if record.used:

            return {
                "msg": "token already used",
                "resend": False 
            }

        # 当前 UTC 时间
        now = datetime.now(timezone.utc)

        user = db.query(User).filter(
            User.id == record.user_id
        ).first()

                # 用户不存在
        if not user:

            return {
                "msg": "user not found",
                "resend": False 
            }

        # token 过期
        if record.expires_at < now:

            email = user.email

            return {
                "msg": "token expired",
                "email": email,
                "resend": True

            }



        # 设置邮箱已验证
        user.is_email_verified = True

        # 设置 token 已使用
        record.used = True

        db.commit()

        return {
            "msg": "email verified successfully",
            "resend": False 
        }

    finally:

        db.close()


# =========================
# 查询邮箱验证状态
# =========================
@app.get("/user/check_verification")
def check_verification(email: str):

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

        db.close()


# =========================
# 重发邮箱验证邮件
# =========================
@app.post("/user/resend_verification_email")
def resend_verification_email(email: str):

    db = SessionLocal()

    try:

        # 查找用户
        user = db.query(User).filter(
            User.email == email
        ).first()

        # 用户不存在
        if not user:

            return {
                "msg":
                "if this email exists, a verification email has been sent"
            }

        # 已验证
        if user.is_email_verified:

            return {
                "msg": "email already verified"
            }

        # 生成 token
        token = generate_token()

        # 创建验证 token
        verification = EmailVerificationToken(
            user_id=user.id,
            token=token,
            expires_at=datetime.now(timezone.utc)
            + timedelta(hours=24)
        )

        db.add(verification)

        db.commit()

        # 邮箱验证链接
        verification_link = (
            f"http://localhost:5173/user/verify_register_email?token={token}"
        )

        # 发送邮件
        send_email(
            to_email=user.email,

            subject="Please verify your email",

            body=f"""
Please verify your email by clicking the link below:

{verification_link}

This link will expire in 24 hours.
"""
        )

        return {
            "msg": "verification email sent"
        }

    finally:

        db.close()


