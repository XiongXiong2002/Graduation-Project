# third-party dependencies
from pydantic import BaseModel

class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str
