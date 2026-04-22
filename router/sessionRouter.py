from database import SessionLocal
from tables.sessions import Session 
from schames.session_create import session_create_request
from tables.message import Message
from schames.msg import msgRequest  
from fastapi import APIRouter


app = APIRouter()

@app.post("/sessions/create")
def create_session( request: session_create_request):
    db = SessionLocal()
    try:
        session = db.query(Session).filter((Session.req_user_id == request.req_user_id)&(Session.state == "open")).first()
        if session:
            return {"msg": "you have an open session", "session_id": session.id}
        new_session = Session(
            req_user_id=request.req_user_id,
            acc_user_id=request.acc_user_id,
            state="open"
        )
        db.add(new_session)
        db.commit()
        db.refresh(new_session)
        return {"session_id": new_session.id}
    finally:
        db.close()


@app.post("/sessions/close")
def close_session(session_id: int): 
    db = SessionLocal()
    session = db.query(Session).filter(Session.id == session_id).first()
    if not session:
        return {"msg": "session not found"}
    try:
        if session.state == "closed":
            return {"msg": "already closed"}
        session.state = "closed"
        db.commit()
        return {"msg": "session closed"}
    finally:
        db.close()

@app.get("/sessions/{session_id}/messages")
def get_messages(session_id: int):
    db = SessionLocal()
    session = db.query(Session).filter(Session.id == session_id).first()
    if not session:
        return {"msg": "session not found"}
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

@app.get("/sessions/{user_id}")
def get_sessions(user_id: int):
    db = SessionLocal()
    try:
        sessions = db.query(Session).filter((Session.req_user_id == user_id) | (Session.acc_user_id == user_id)).order_by(Session.created_at.desc()).all()
        return [{
            "id": session.id,
            "req_user_id": session.req_user_id,
            "acc_user_id": session.acc_user_id,
            "state": session.state,
            "created_at": session.created_at
        } for session in sessions]
    finally:
        db.close()