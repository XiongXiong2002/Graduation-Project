from typing import Optional

from pydantic import BaseModel ,EmailStr

class registerRequest(BaseModel):
    email: EmailStr
    password: str   
    role : str
    username: str
    status: Optional[str] =None
    problem_type: Optional[str] = None
    preference: Optional[str] = None
    # 学校信息
    institution:str
    # 专业信息
    programme:str
    # 当前地区
    location: str
