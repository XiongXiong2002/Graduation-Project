# standard library
from typing import Optional

# third-party dependencies
from pydantic import BaseModel, EmailStr
 
class msgRequest(BaseModel):
    session_id: int
    sender_id: Optional[int] = None
    sender_type: str
    content: str
    
