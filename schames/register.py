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