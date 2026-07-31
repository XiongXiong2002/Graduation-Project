# standard library
from typing import Literal, Optional

# third-party dependencies
from pydantic import BaseModel

class session_create_request(BaseModel):
    # AI 会话没有接收用户，因此允许 acc_user_id 为 None。
    acc_user_id: Optional[int] = None
    # 只接受系统目前支持的两种会话类型。
    match_type: Literal["mentor", "ai"] = "mentor"
