from typing import Literal, Optional, Dict, Any
from pydantic import BaseModel


class VoiceSignalMessage(BaseModel):

    # signaling 消息类型
    #
    # 这里只允许四种消息：
    #
    # voice_offer
    #     发起语音连接
    #
    # voice_answer
    #     接受语音连接
    #
    # ice_candidate
    #     WebRTC 网络协商信息
    #
    # voice_end
    #     主动结束语音通话
    #
    # Literal 表示：
    # type 只能是下面几个字符串之一
    # 如果前端发送其它字符串
    # Pydantic 会自动校验失败
    type: Literal[
        "voice_offer",
        "voice_answer",
        "ice_candidate",
        "voice_end"
    ]

    # signaling 消息内容
    #
    # 不同类型对应不同数据：
    #
    # voice_offer
    #     payload = {"offer": ...}
    #
    # voice_answer
    #     payload = {"answer": ...}
    #
    # ice_candidate
    #     payload = {"candidate": ...}
    #
    # voice_end
    #     不需要额外数据
    #     payload = None
    #
    # Optional
    #     表示可以为空
    #
    # Dict[str, Any]
    #     表示：
    #     key 必须是字符串
    #     value 可以是任意类型
    #
    # WebRTC 的 offer / answer / candidate
    # 本身就是复杂 JSON
    # 所以后端不解析
    # 直接原样转发给另一端
    payload: Optional[Dict[str, Any]] = None