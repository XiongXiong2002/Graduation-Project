# third-party dependencies
from pydantic import BaseModel

class CheckResetTokenRequest(BaseModel):
    token: str
