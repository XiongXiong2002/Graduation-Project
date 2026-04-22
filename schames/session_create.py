from typing import Optional
from pydantic import BaseModel ,EmailStr

class session_create_request(BaseModel):
    req_user_id: int
    acc_user_id: Optional[int] = None