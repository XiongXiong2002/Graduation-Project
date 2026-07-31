# third-party dependencies
from pydantic import BaseModel

class BlockInfo(BaseModel):
    blocker_id:int
    blocked_id:int
    reason: str | None = None

    
