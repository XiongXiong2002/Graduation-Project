# third-party dependencies
from pydantic import BaseModel, EmailStr
 
class loginRequest(BaseModel):
    email: EmailStr
    password: str

    
