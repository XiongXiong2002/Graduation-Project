# third-party dependencies
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError

# authentication
from auth import get_current_user

# database
from database import SessionLocal

# request schema
from schames.session_create import session_create_request
from schames.session_close_info import session_close_info

# database tables
from tables.matchPool import MatchPool
from tables.message import Message
from tables.sessions import Session
from tables.user import User

# routers
from router.matchRouter import find_match_for_user

# services
from service.websocket_manager import manager
from service.ai_service import update_ai_summary


app = APIRouter()

@app.post("/sessions/create")
def create_session(
    session_create_info: session_create_request,
    current_user: User = Depends(get_current_user)
):
    # =========================
    # 只有 Student 可以主动创建 Session
    # Mentor 只能等待学生选择
    # =========================
    if current_user.role != "student":
        raise HTTPException(status_code=403, detail="only student can create session")

    db = SessionLocal()

    try:

        # =========================
        # 获取双方用户信息
        # =========================
        req_user_id = current_user.id
        acc_user_id = session_create_info.acc_user_id
        match_type = session_create_info.match_type

        # Mentor 会话必须关联真实导师；AI 会话不关联任何接收用户。
        if match_type == "mentor" and acc_user_id is None:
            raise HTTPException(status_code=400, detail="mentor session requires acc_user_id")

        if match_type == "ai" and acc_user_id is not None:
            raise HTTPException(status_code=400, detail="AI session acc_user_id must be null")

        # =========================
        # 检查学生是否已有进行中的 Session
        # 一个学生同时只能拥有一个会话
        # =========================
        existing_student_session = db.query(Session).filter(
            Session.req_user_id == req_user_id,
            Session.state == "open"
        ).first()

        if existing_student_session:
            return {
                "msg": "you already have an open session",
                "session_id": existing_student_session.id,
                "match_type": existing_student_session.match_type,
                "acc_user_id": existing_student_session.acc_user_id
            }

        # =========================
        # 检查 Mentor 是否仍然在匹配池中
        #
        # 防止：
        # - Mentor 已退出匹配
        # - Mentor 已被其他学生抢先匹配
        # =========================
        # AI 会话没有 Mentor，因此跳过匹配池检查。
        pool_item = None
        if match_type == "mentor":
            pool_item = db.query(MatchPool).filter(
                MatchPool.mentor_id == acc_user_id,
            ).first()

            if not pool_item:
                raise HTTPException(status_code=409, detail="selected user is no longer available")

        # =========================
        # 检查 Mentor 是否已有进行中的 Session
        # 一个 Mentor 同时只能服务一个学生
        # =========================
        # 只有 Mentor 会话才需要检查导师是否已在其他会话中。
        existing_mentor_session = None
        if match_type == "mentor":
            existing_mentor_session = db.query(Session).filter(
                Session.acc_user_id == acc_user_id,
                Session.state == "open"
            ).first()

        if existing_mentor_session:

            # Mentor 已经进入 Session
            # 顺便将其从 MatchPool 中移除
            db.delete(pool_item)
            db.commit()

            raise HTTPException(status_code=409, detail="selected user already has an open session")

        # =========================
        # 创建新的 Session
        # =========================
        new_session = Session(
            req_user_id=req_user_id,
            acc_user_id=acc_user_id,
            match_type=match_type,
            state="open"
        )

        db.add(new_session)

        # =========================
        # 创建成功后移出匹配池
        #
        # 防止 Mentor 再次被其他学生选择
        # =========================
        # AI 会话的 pool_item 为 None，不执行匹配池删除。
        if pool_item is not None:
            db.delete(pool_item)

        # =========================
        # 提交数据库事务
        # =========================
        try:
            db.commit()
            db.refresh(new_session)

        except IntegrityError:

            # 数据库唯一约束触发
            # 一般是高并发下重复创建 Session
            db.rollback()

            existing_session = db.query(Session).filter(
                Session.req_user_id == req_user_id,
                Session.state == "open"
            ).first()

            if existing_session:
                return {
                    "msg": "you already have an open session",
                    "session_id": existing_session.id,
                    "match_type": existing_session.match_type,
                    "acc_user_id": existing_session.acc_user_id
                }

            raise HTTPException(status_code=409, detail="session already exists")

        # =========================
        # 返回创建成功的信息
        # =========================
        return {
            "msg": "session created",
            "session_id": new_session.id,
            "match_type": match_type,
            "acc_user_id": acc_user_id
        }

    finally:
        db.close()

@app.post("/sessions/close")
async def close_session_api(session_info:session_close_info,current_user: User = Depends(get_current_user)):
    # 1.先发送通知给前端，告知 session 已关闭
    await manager.broadcast(session_info.seesion_id,{"type": "session_closed"})

    # 2. 再关闭数据库 session
    result = close_session_by_id(session_info.seesion_id, current_user.id)

    # 3. 再关闭该 session 下所有 websocket 连接
    await manager.close(session_info.seesion_id)

    if session_info.match_type == "ai":
        update_ai_summary(current_user.id,session_info.seesion_id)

    return result

    





@app.get("/sessions/{session_id}/messages")
def get_messages(session_id: int, current_user: User = Depends(get_current_user)):
    db = SessionLocal()
    session = db.query(Session).filter(Session.id == session_id).first()
    if not session:
        return {"msg": "session not found"}
    if session.req_user_id != current_user.id and session.acc_user_id != current_user.id:
        raise HTTPException(status_code=403, detail="you are not part of this session")
    try:
        
        messages = db.query(Message).filter(Message.session_id == session_id).order_by(Message.timestamp).all()
        return [{
                "id": m.id,
                "session_id": m.session_id,
                "sender_id": m.sender_id,
                "sender_type": m.sender_type,
                "content": m.content,
                "timestamp": m.timestamp
                } for m in messages]
    finally:
        db.close()

@app.get("/sessions/get")
def get_sessions(current_user: User = Depends(get_current_user)):
    db = SessionLocal()
    try:
        sessions = db.query(Session).filter((Session.req_user_id == current_user.id) | (Session.acc_user_id == current_user.id)).order_by(Session.created_at.desc()).all()
        return [{
            "id": session.id,
            "req_user_id": session.req_user_id,
            "acc_user_id": session.acc_user_id,
            "state": session.state,
            "created_at": session.created_at
        } for session in sessions]
    finally:
        db.close()

@app.get("/sessions/open")
def get_open_session(
    current_user: User = Depends(get_current_user)
):
    db = SessionLocal()

    try:

        # =========================
        # 查询当前用户是否存在 open session
        #
        # 同时检查：
        # 1. 当前用户是学生(req_user)
        # 2. 当前用户是导师(acc_user)
        #
        # 防止用户通过：
        # - 浏览器历史记录
        # - 手动输入 URL
        # - 修改前端代码
        #
        # 绕过聊天页面
        # =========================
        session = db.query(Session).filter(
            (
                (Session.req_user_id == current_user.id) |
                (Session.acc_user_id == current_user.id)
            ) &
            (Session.state == "open")
        ).first()

        # =========================
        # 当前没有 open session
        # =========================
        if not session:

            return {
                "msg": "no open session"
            }

        # =========================
        # 返回当前 open session
        #
        # 前端可以根据返回结果：
        # navigate(`/chat/${session.id}`)
        # =========================
        return {
            "id": session.id,
            "req_user_id": session.req_user_id,
            "acc_user_id": session.acc_user_id,
            "match_type": session.match_type,
            "state": session.state,
            "created_at": session.created_at
        }

    finally:

        db.close()


def close_session_by_id(session_id: int, current_user_id: int):
    db = SessionLocal()

    try:
        session = db.query(Session).filter(Session.id == session_id).first()

        if not session:
            return {"msg": "session not found"}

        if (session.req_user_id != current_user_id and session.acc_user_id != current_user_id):
            raise HTTPException(status_code=403, detail="you are not part of this session")

        if session.state == "closed":
            return {"msg": "already closed"}

        # 1. 关闭 session
        session.state = "closed"

        # 2. 清理双方在匹配池里的残留
        # AI session 的 acc_user_id 为 None，不参与 Mentor 匹配池清理。
        if session.acc_user_id is not None:
            db.query(MatchPool).filter(
                MatchPool.mentor_id == session.acc_user_id
            ).delete(synchronize_session=False)

        # 3. 一次性提交
        db.commit()

        return {"msg": "session closed"}

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()
