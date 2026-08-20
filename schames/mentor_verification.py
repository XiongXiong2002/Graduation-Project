from pydantic import BaseModel, EmailStr


class MentorVerificationRequest(BaseModel):
    # 注册账号使用的邮箱，用于定位等待 Mentor 验证的用户
    account_email: EmailStr
    # Mentor 在验证方式页面填写的学校邮箱；只用于校验后缀和发送邮件
    mentor_email: EmailStr
