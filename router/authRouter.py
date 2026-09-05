# standard library
from datetime import datetime, timedelta, timezone
from typing import Annotated

# third-party dependencies
from fastapi import APIRouter, Form

# database
from database import SessionLocal

# request schema
from schames.login import loginRequest
from schames.register import registerRequest
from schames.reset import ResetPasswordRequest
from schames.check_reset import CheckResetTokenRequest
from schames.mentor_verification import MentorVerificationRequest

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
    VALID_UNIVERSITIES,
    VALID_CITIES,
    VALID_PROBLEM_TYPES,
    VALID_STATUSES,
    VALID_ACADEMIC_LEVELS,
    verify_mentor_email
)
from tools.avatar import save_approved_avatar

# token generator
from tools.token_create import generate_token

# email service
from service.email_service import send_email

# 创建 router
app = APIRouter()



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

        # 密码错误时不暴露邮箱或 Mentor 审核状态。
        if not verify_password(user.password, matched_user.password_hash):
            return {
                "msg": "invalid email or password"
            }

        # 邮箱未验证
        if not matched_user.is_email_verified:

            return {
                "msg": "email not verified",
                "email": matched_user.email
            }

        if matched_user.role == "mentor":
            # 人工审核中的 Mentor 保持未登录，只向前端返回审核中状态。
            if matched_user.mentor_verify_status == "pending":
                return {
                    "msg": "mentor verification pending"
                }

            # disapprove 承接原 Boolean False：进入 Mentor 验证方式页面。
            if matched_user.mentor_verify_status == "disapprove":
                return {
                    "msg": "mentor not verified",
                    "email": matched_user.email
                }

        # 密码、邮箱和 Mentor 资格均已通过。
        if matched_user.role != "mentor" or matched_user.mentor_verify_status == "approve":
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
                    "academic_level": matched_user.academic_level,
                    "institution": matched_user.institution,
                    "programme": matched_user.programme,
                    "location": matched_user.location,
                    # 头像上传修改（后端生成头像地址）：登录响应把数据库 user 中的头像地址交给前端 user_info。
                    "img": matched_user.photo,
                    "motto": matched_user.motto
                }
            
            }
            
    finally:

        db.close()


# =========================
# 用户注册
# =========================
@app.post("/user/register")
def register(
    # 头像上传修改（后端生成头像地址）：完整注册 schema 直接从 multipart FormData 读取。
    user: Annotated[registerRequest, Form()]
):
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
        academic_level = user.academic_level

        if not user.username.strip():

            return {
                "msg": "invalid username"
            }

        if user.role not in {"student", "mentor"}:

            return {
                "msg": "invalid role"
            }

        if status not in VALID_STATUSES:

            return {
                "msg": "invalid status"
            }

        if problem_type not in VALID_PROBLEM_TYPES:

            return {
                "msg": "invalid problem type"
            }

        if academic_level not in VALID_ACADEMIC_LEVELS:
            return {
                "msg": "invalid academic level"
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

        # 头像上传修改（后端生成头像地址）：同一请求检测头像；未上传时使用后端默认图标。
        avatar_path = save_approved_avatar(user.img)

        new_user = User(
            username=user.username.strip(),
            email=user.email,
            password_hash=hash_password(user.password),
            role=user.role,
            status=status,
            problem_type=problem_type,
            academic_level=academic_level,
            institution=user.institution,
            programme=user.programme.strip(),
            location=user.location,
            # 头像上传修改（后端生成头像地址）：user.photo 只保存后端批准并生成的头像地址。
            photo=avatar_path,
            mentor_verify_status="disapprove",
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
    
                    http://studentpeersupport.com/user/verify_register_email?token={token}

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
            f"http://studentpeersupport.com/reset_password?token={token}"
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

        # 邮箱验证只接受 purpose=register，其他用途的 token 无法用于验证注册邮箱。
        record = db.query(
            EmailVerificationToken
        ).filter(
            EmailVerificationToken.token == token,
            EmailVerificationToken.purpose == "register"
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
        verification = EmailVerificationToken( user_id=user.id,token=token,expires_at=datetime.now(timezone.utc)+ timedelta(hours=24))

        db.add(verification)

        db.commit()

        # 邮箱验证链接
        verification_link = (
            f"http://studentpeersupport.com/user/verify_register_email?token={token}"
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

# =========================
# Mentor 学校邮箱验证接口
# =========================
@app.get("/user/verify_mentor_email")
def verify_mentor_email_token(token: str):
    # 每次请求单独创建数据库会话，结束时统一关闭
    db = SessionLocal()

    try:
        # 根据邮件链接中的 token 查找验证记录
        record = db.query(EmailVerificationToken).filter(
            EmailVerificationToken.token == token,
            EmailVerificationToken.purpose == "mentor"
        ).first()

        # token 不存在，拒绝本次验证
        if not record:
            return {"msg": "invalid token", "resend": False}

        # token 只能使用一次，防止重复验证
        if record.used:
            return {"msg": "token already used", "resend": False}

        # 通过验证记录中的 user_id 查找对应用户
        user = db.query(User).filter(
            User.id == record.user_id
        ).first()

        # 验证记录对应的用户不存在
        if not user:
            return {"msg": "user not found", "resend": False}

        # token 已过期，返回邮箱供后续重新发送验证邮件
        if record.expires_at < datetime.now(timezone.utc):
            return {
                "msg": "token expired",
                "email": user.email,
                "resend": True
            }

        # 该接口只允许验证 Mentor 用户
        if user.role != "mentor":
            return {"msg": "user is not a mentor", "resend": False}


        # 标记 Mentor 资格验证成功，并将 token 设置为已使用
        user.mentor_verify_status = "approve"
        record.used = True


        # 同一个事务保存用户状态和 token 状态
        db.commit()

        return {
            "msg": "mentor email verified successfully",
            "resend": False
        }

    finally:
        # 无论验证成功还是失败，都关闭数据库会话
        db.close()


@app.get("/user/get_mentor_verification")
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

            # 供 Mentor 验证方式页面轮询身份验证状态
            return {
                "verified": user.mentor_verify_status == "approve",
                "status": user.mentor_verify_status
            }

        finally:
            
            db.close()

@app.post("/user/send_mentor_verification_email")
def send_mentor_verification_email(request: MentorVerificationRequest):
    # 该接口只发送学校邮箱验证邮件，不重复发送普通注册邮箱邮件。
    db = SessionLocal()
    
    try:
            # 查找用户
        user = db.query(User).filter(
            User.email == request.account_email
        ).first()
    
            # 用户不存在
        if not user:
            return {"msg":"if this email exists, a verification email has been sent"}
    
            # 已验证
        if user.mentor_verify_status == "approve":
    
            return {"msg": "mentor already verified"}

        if user.role != "mentor":
            return {"msg": "user is not a mentor"}

        # 必须先完成普通注册邮箱验证，才能开始 Mentor 学校邮箱验证。
        if not user.is_email_verified:
            return {"msg": "account email not verified"}

        # 使用 Mentor 验证页本次选择的学校校验邮箱后缀。
        # 这样注册时误选学校不会导致用户无法完成 Mentor 验证。
        is_mentor_email_valid = verify_mentor_email(
            request.institution,
            str(request.mentor_email)
        )
        
        if  is_mentor_email_valid:
            # 只生成学校邮箱验证 token；注册邮箱在注册阶段已经完成验证。
            mentor_token = generate_token()

            # 与普通注册邮箱共用 token 表，通过 purpose 区分用途。
            mentor_verification = EmailVerificationToken(
                user_id=user.id,
                token=mentor_token,
                purpose="mentor",
                expires_at=datetime.now(timezone.utc)
                + timedelta(hours=24)
            )
    
            db.add(mentor_verification)

            db.commit()
    
            mentor_verification_link = (
                f"http://studentpeersupport.com/user/verify_mentor_email?token={mentor_token}"
            )

            # 向学校邮箱发送 Mentor 身份验证邮件。
            send_email(
                to_email=str(request.mentor_email),
                subject="Please verify your university email",
                body=f"""
                        Please verify your university email by clicking the link below:

                        {mentor_verification_link}

                        This link will expire in 24 hours.
                    """
            )
    
            return {
                "msg": "mentor verification email sent"
            }
    
    finally:
    
            db.close()



