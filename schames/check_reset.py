from pydantic import BaseModel

class CheckResetTokenRequest(BaseModel):
    token: str
