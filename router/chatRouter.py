# third-party dependencies
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import ValidationError  # 【新增：捕获 WebSocket 消息校验错误】

# authentication
from auth import get_user_id

# database
from database import SessionLocal

# 【新增：统一校验文字、AI 和语音信令的 WebSocket schema】
from schames.signal_message import SignalMessage

# database tables
from tables.message import Message
from tables.sessions import Session

# routers
from router.sessionRouter import close_session_by_id

# services
from service.ai_service import ask_ai_result
from service.websocket_manager import manager


app = APIRouter()



@app.websocket("/ws/chat")
async def chat_ws(websocket: WebSocket, token: str):
    session_id = None
    session_match_type = None

    try:
        # 1. 连接建立时先验证 token
        user_id = get_user_id(token)

        # 2. 查当前用户的 open session
        db = SessionLocal()
        try:
            session = db.query(Session).filter(
                (
                    (Session.req_user_id == user_id) |
                    (Session.acc_user_id == user_id)
                ) &
                (Session.state == "open")
            ).first()
            session_id = session.id if session else None
            # 保存会话类型，数据库连接关闭后仍可判断是否允许语音信令。
            session_match_type = session.match_type if session else None
        finally:
            db.close()

        if session_id is None:
            await websocket.accept()
            await websocket.send_json({"error": "no open session"})
            await websocket.close()
            return

        # 3. 接入连接池
        await manager.connect(session_id, websocket)

        try:
            while True:
                data = await websocket.receive_json()

                # 【新增：所有收到的消息必须符合 type + content 结构】
                try:
                    incoming_message = SignalMessage.model_validate(data)
                except ValidationError:
                    await websocket.send_json({"error": "invalid websocket message"})
                    continue

                # 【新增：将校验后的模型转回统一的 type + content 字典】
                data = incoming_message.model_dump()

                # 4. 每次收到消息后，再验证一次 token 是否过期
                try:
                    get_user_id(token)

                except HTTPException:
                    # 1. 先通知前端
                    await websocket.send_json({"error": "token expired"})

                    # 2. 关闭当前 session 下所有 websocket 连接
                    await manager.close(session_id)

                    # 3. 再关闭数据库里的 session
                    close_session_by_id(session_id, user_id)

                    return
                
                # 【新增：直接使用 schema 已校验的消息类型】
                msg_type = incoming_message.type

                # 语音 / WebRTC 信令：只转发，不保存数据库
                if msg_type in [
                    "voice_request",
                    "voice_accept",
                    "voice_reject",
                    "voice_end",
                    "voice_offer",
                    "voice_answer",
                    "ice_candidate",
                ]:
                    # AI session 没有第二位通话参与者，禁止转发任何语音信令。
                    if session_match_type == "ai":
                        await websocket.send_json({"error": "voice is not available for AI sessions"})
                        continue

                    # 【新增：转发 schema 标准化后的语音信令】
                    await manager.broadcast(session_id, data)
                    continue

                # 【新增：schema 已保证文字和 AI 消息的 content 是非空字符串】
                content = data["content"].strip()

                new_message = Message(
                    session_id=session_id,
                    sender_id=user_id,
                    sender_type="user",
                    content=content 
                )

                # 每条用户消息使用独立的短生命周期数据库会话
                db = SessionLocal()
                try:
                    db.add(new_message)
                    db.commit()
                    db.refresh(new_message)
                    message_data = {
                        "type": "text_message",
                        "id": new_message.id,
                        "session_id": new_message.session_id,
                        "sender_id": new_message.sender_id,
                        "sender_type": new_message.sender_type,
                        "content": new_message.content,
                        "timestamp": str(new_message.timestamp)
                    }
                except Exception:
                    db.rollback()
                    raise
                finally:
                    db.close()

                await manager.broadcast(session_id, message_data)
                
                if msg_type == "ask_for_ai":
                    content = ask_ai_result(user_id,session_id,content)

                    new_message = Message(
                    session_id=session_id,
                    sender_id=None,
                    sender_type="ai",
                    content=content 
                    )
                    # AI 回复生成后使用新的短生命周期数据库会话
                    db = SessionLocal()
                    try:
                        db.add(new_message)
                        db.commit()
                        db.refresh(new_message)
                        message_data = {
                            "type": "text_message",
                            "id": new_message.id,
                            "session_id": new_message.session_id,
                            "sender_id": new_message.sender_id,
                            "sender_type": new_message.sender_type,
                            "content": new_message.content,
                            "timestamp": str(new_message.timestamp)
                        }
                    except Exception:
                        db.rollback()
                        raise
                    finally:
                        db.close()
                
                    await manager.broadcast(session_id, message_data)
                



        except WebSocketDisconnect:
            print("broken")
            manager.disconnect(session_id, websocket)

    except Exception as e:
        try:
            await websocket.accept()
            await websocket.send_json({"error": str(e)})
            await websocket.close()
        except Exception:
            pass


