from auth import get_current_user
from database import SessionLocal
from router.matchRouter import find_match_for_user
from tables.sessions import Session 

from tables.message import Message
from schames.msg import msgRequest  
from fastapi import APIRouter
from fastapi import Depends, HTTPException

from tables.user import User


app = APIRouter()

@app.post("/sessions/create")
def create_session(
    current_user: User = Depends(get_current_user)
):
    db = SessionLocal()

    try:
        req_user_id = current_user.id

        session = db.query(Session).filter(
            (Session.req_user_id == req_user_id) &
            (Session.state == "open")
        ).first()

        if session:
            return {
                "msg": "you have an open session",
                "session_id": session.id
            }

        match_result = find_match_for_user(req_user_id, db)

        if match_result["match_type"] == "none":
            return {
                "msg": "no mentor available"
            }

        acc_user_id = match_result["acc_user_id"]

        new_session = Session(
            req_user_id=req_user_id,
            acc_user_id=acc_user_id,
            state="open"
        )

        db.add(new_session)
        db.commit()
        db.refresh(new_session)

        return {
            "session_id": new_session.id,
            "match_type": match_result["match_type"],
            "acc_user_id": acc_user_id
        }

    finally:
        db.close()


@app.post("/sessions/close")
def close_session(session_id: int, current_user: User = Depends(get_current_user)): 
    db = SessionLocal()
    try:
        session = db.query(Session).filter(Session.id == session_id).first()

        if not session:
            return {"msg": "session not found"}

        if session.req_user_id != current_user.id and session.acc_user_id != current_user.id:
            raise HTTPException(status_code=403, detail="you are not part of this session")

        if session.state == "closed":
            return {"msg": "already closed"}

        session.state = "closed"
        db.commit()

        return {"msg": "session closed"}

    finally:
        db.close()

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
def get_open_session(current_user: User = Depends(get_current_user)):
    db = SessionLocal()
    try:
        session = db.query(Session).filter(
            ((Session.req_user_id == current_user.id) | (Session.acc_user_id == current_user.id)) &
            (Session.state == "open")
        ).first()

        if not session:
            return {"msg": "no open session"}

        return {
            "id": session.id,
            "req_user_id": session.req_user_id,
            "acc_user_id": session.acc_user_id,
            "state": session.state,
            "created_at": session.created_at
        }
    finally:
        db.close()