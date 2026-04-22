from pydantic import BaseModel ,EmailStr
from typing import Optional

class personalInfoRequest(BaseModel):
    email: Optional[EmailStr] = None
    username: Optional[str] = None
    role: Optional[str] = None
    status: Optional[str] =None
    problem_type: Optional[str] = None
    preference: Optional[str] = None