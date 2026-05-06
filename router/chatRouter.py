from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from service.websocket_manager import ConnectionManager

app = APIRouter()
manager = ConnectionManager()

from fastapi import WebSocket, WebSocketDisconnect, APIRouter,Depends
from pydantic import ValidationError

from auth import verify_token

from database import SessionLocal
from service.websocket_manager import ConnectionManager
from schames.ws_message import WSMessageRequest
from tables.sessions import Session
from tables.message import Message

app = APIRouter()

@app.websocket("/ws/chat")
async def chat_ws(websocket: WebSocket, token: str):
    db = SessionLocal()

    try:
        # 1. 验证 token，拿到 user_id
        user_id = verify_token(token)

        # 2. 查当前用户的 open session
        session = db.query(Session).filter(
            (
                (Session.req_user_id == user_id) |
                (Session.acc_user_id == user_id)
            ) &
            (Session.state == "open")
        ).first()

        if not session:
            await websocket.accept()
            await websocket.send_json({"error": "no open session"})
            await websocket.close()
            return

        session_id = session.id

        # 3. 接入连接池
        await manager.connect(session_id, websocket)

        try:
            while True:
                data = await websocket.receive_json()

                content = data.get("content", "").strip()

                if not content:
                    await websocket.send_json({"error": "empty message"})
                    continue

                new_message = Message(
                    session_id=session_id,
                    sender_id=user_id,
                    sender_type="user",
                    content=content
                )

                db.add(new_message)
                db.commit()
                db.refresh(new_message)

                await manager.broadcast(session_id, {
                    "id": new_message.id,
                    "session_id": new_message.session_id,
                    "sender_id": new_message.sender_id,
                    "sender_type": new_message.sender_type,
                    "content": new_message.content,
                    "timestamp": str(new_message.timestamp)
                })

        except WebSocketDisconnect:
            manager.disconnect(session_id, websocket)

    except Exception as e:
        await websocket.accept()
        await websocket.send_json({"error": str(e)})
        await websocket.close()

    finally:
        db.close()