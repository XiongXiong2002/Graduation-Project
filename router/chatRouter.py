from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from service.websocket_manager import ConnectionManager

app = APIRouter()
manager = ConnectionManager()

from fastapi import WebSocket, WebSocketDisconnect, APIRouter
from pydantic import ValidationError

from database import SessionLocal
from service.websocket_manager import manager
from schames.ws_message import WSMessageRequest
from tables.sessions import Session
from tables.message import Message

app = APIRouter()

@app.websocket("/ws/chat/{session_id}/{user_id}")
async def chat_ws(websocket: WebSocket, session_id: int, user_id: int):
    db = SessionLocal()

    # 先检查 session 是否存在
    session = db.query(Session).filter(Session.id == session_id).first()
    if not session:
        await websocket.accept()
        await websocket.send_json({"error": "session not found"})
        await websocket.close()
        db.close()
        return

    # 检查该用户是否属于这个 session
    if user_id != session.req_user_id and user_id != session.acc_user_id:
        await websocket.accept()
        await websocket.send_json({"error": "user not allowed in this session"})
        await websocket.close()
        db.close()
        return

    # 检查 session 是否已关闭
    if session.state == "closed":
        await websocket.accept()
        await websocket.send_json({"error": "session already closed"})
        await websocket.close()
        db.close()
        return

    await manager.connect(session_id, websocket)

    try:
        while True:
            data = await websocket.receive_json()

            try:
                msg = WSMessageRequest(**data)
            except ValidationError:
                await websocket.send_json({"error": "invalid message format"})
                continue

            content = msg.content.strip()
            if not content:
                await websocket.send_json({"error": "empty message"})
                continue

            # 入库
            new_message = Message(
                session_id=session_id,
                sender_id=user_id,
                sender_type="user",
                content=content
            )
            db.add(new_message)
            db.commit()
            db.refresh(new_message)

            # 组装广播消息
            message = {
                "id": new_message.id,
                "session_id": new_message.session_id,
                "sender_id": new_message.sender_id,
                "sender_type": new_message.sender_type,
                "content": new_message.content,
                "timestamp": str(new_message.timestamp)
            }

            # 广播
            await manager.broadcast(session_id, message)

    except WebSocketDisconnect:
        manager.disconnect(session_id, websocket)

    finally:
        db.close()