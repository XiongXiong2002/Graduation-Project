# standard library
from typing import Optional

# third-party dependencies
from pydantic import BaseModel, EmailStr

class personalInfoRequest(BaseModel):
    email: Optional[EmailStr] = None
    username: Optional[str] = None
    role: Optional[str] = None
    status: Optional[str] =None
    problem_type: Optional[str] = None

    # 学校信息
    institution:Optional[str] = None
    # 专业信息
    programme:Optional[str] = None
    # 当前地区
    location: Optional[str] = None
    #选择图片
    # 修改资料时可以选择新的合法头像路径。
    img: Optional[str] = None
    #格言
    # 修改资料时可以更新个人格言。
    motto: Optional[str] = None


