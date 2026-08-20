from fastapi import UploadFile
from pydantic import BaseModel, EmailStr


class MentorVerifyInfo(BaseModel):
    # 注册账号使用的邮箱，用于定位等待 Mentor 验证的用户
    account_email: EmailStr
    #注册账号的密码
    account_password: str
    # 上传的文件
    uploaded_file: UploadFile