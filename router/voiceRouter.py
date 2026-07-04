from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from pydantic import ValidationError

from auth import verify_token
from database import SessionLocal
from service.voice_manager import voice_manager
from tables.sessions import Session
from schames.VoiceSignalMessage import VoiceSignalMessage


app = APIRouter()


@app.websocket("/ws/voice/{session_id}")
async def voice_ws(
    websocket: WebSocket,
    session_id: int,
    token: str
):
    db = SessionLocal()

    try:
        # 1. 验证 token
        user_id = verify_token(token)

        # 2. 查询指定 session
        session = db.query(Session).filter(
            Session.id == session_id,
            Session.state == "open"
        ).first()

        # 3. 检查 session 是否存在
        if not session:
            await websocket.accept()
            await websocket.send_json({"error": "session not found or closed"})
            await websocket.close()
            return

        # 4. 检查当前用户是否属于这个 session
        if user_id not in [
            session.req_user_id,
            session.acc_user_id
        ]:
            await websocket.accept()
            await websocket.send_json({"error": "not allowed to join this voice session"})
            await websocket.close()
            return

        # 5. 加入 voice websocket 连接池
        await voice_manager.connect(
            session_id,
            user_id,
            websocket
        )

        try:
            while True:
                # 6. 接收前端发来的 signaling JSON
                data = await websocket.receive_json()

                # 7. 每次收到消息时重新验证 token
                try:
                    verify_token(token)

                except HTTPException:
                    await websocket.send_json({"error": "token expired"})
                    await websocket.close()
                    return

                # 8. 使用 Pydantic schema 校验消息格式
                try:
                    voice_message = VoiceSignalMessage(**data)

                except ValidationError:
                    await websocket.send_json({"error": "invalid voice signal message"})
                    continue

                # 9. 转发给同一个 session 中的另一方
                await voice_manager.send_to_others(
                    session_id,
                    user_id,
                    {
                        "type": voice_message.type,
                        "user_id": user_id,
                        "payload": voice_message.payload
                    }
                )

        except WebSocketDisconnect:
            await voice_manager.disconnect(
                session_id,
                user_id
            )

    except Exception as e:
        try:
            await websocket.accept()
            await websocket.send_json({"error": str(e)})
            await websocket.close()
        except Exception:
            pass

    finally:
        db.close()