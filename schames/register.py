# standard library
from typing import Optional

# third-party dependencies
from fastapi import UploadFile
from pydantic import BaseModel, EmailStr

class registerRequest(BaseModel):
    email: EmailStr
    password: str   
    role : str
    username: str
    status: str
    problem_type: str
    academic_level: int

    # 学校信息
    institution:str
    # 专业信息
    programme:str
    # 当前地区
    location: str
    # 头像上传修改（后端生成头像地址）：完整 FormData schema 中直接接收可选图片文件。
    img: Optional[UploadFile] = None
    #格言
    # 注册时填写的个人格言。
    motto :str
