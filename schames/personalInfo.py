# standard library
from typing import Optional

# third-party dependencies
from fastapi import UploadFile
from pydantic import BaseModel, EmailStr

class personalInfoRequest(BaseModel):
    email: Optional[EmailStr] = None
    username: Optional[str] = None
    role: Optional[str] = None
    status: Optional[str] =None
    problem_type: Optional[str] = None
    academic_level: Optional[int] = None

    # 学校信息
    institution:Optional[str] = None
    # 专业信息
    programme:Optional[str] = None
    # 当前地区
    location: Optional[str] = None
    # 头像上传修改（后端生成头像地址）：完整 FormData schema 中直接接收可选新头像。
    img: Optional[UploadFile] = None
    #格言
    # 修改资料时可以更新个人格言。
    motto: Optional[str] = None


