from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, model_validator


class SignalMessage(BaseModel):
    # 【新增：禁止 type 和 content 之外的额外顶层字段】
    model_config = ConfigDict(extra="forbid")

    # 【新增：统一限制聊天、AI 和 WebRTC 信令允许使用的消息类型】
    type: Literal[
        "text_message",
        "ask_for_ai",
        "voice_request",
        "voice_accept",
        "voice_reject",
        "voice_end",
        "voice_offer",
        "voice_answer",
        "ice_candidate",
    ]
    # 【新增：文字和 AI 使用字符串，语音信令使用 JSON 对象】
    content: str | dict[str, Any]

    # 【新增：根据 type 检查 content 的数据类型和空值】
    @model_validator(mode="after")
    def validate_content(self):
        if self.type in {"text_message", "ask_for_ai"}:
            if not isinstance(self.content, str) or not self.content.strip():
                raise ValueError("text content must be a non-empty string")
        elif not isinstance(self.content, dict):
            raise ValueError("voice signal content must be an object")

        return self
