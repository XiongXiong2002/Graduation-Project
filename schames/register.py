# standard library
from typing import Optional

# third-party dependencies
from pydantic import BaseModel, EmailStr

class registerRequest(BaseModel):
    email: EmailStr
    password: str   
    role : str
    username: str
    status: Optional[str] =None
    problem_type: Optional[str] = None

    # 学校信息
    institution:str
    # 专业信息
    programme:str
    # 当前地区
    location: str
    #选择图片
    # 注册时选择的合法头像路径。
    img :str
    #格言
    # 注册时填写的个人格言。
    motto :str
