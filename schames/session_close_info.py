
# third-party dependencies
from typing import Literal

from pydantic import BaseModel

class session_close_info(BaseModel):
    seesion_id: int
    # 当前 session 类型，只允许 AI 或 Mentor。
    match_type: Literal["mentor", "ai"]
