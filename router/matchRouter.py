from datetime import datetime, timezone
from tables.user import User
from database import SessionLocal
from tables.match_pool import MatchPool
from fastapi import APIRouter

app = APIRouter()

@app.post("/match/join")
def get_match(user_id: int):
    db = SessionLocal()
    try:
        current_user = db.query(User).filter(User.id == user_id).first()
        if not current_user:
            return {"msg": "user not found"}
        match =  MatchPool(
            user_id=user_id,
            status=current_user.status,
            problem_type=current_user.problem_type
            )
        db.add(match)
        db.commit()
    finally:
        db.close()

@app.post("/match/{user_id}/heartbeat")
def heartbeat(user_id: int):
    db = SessionLocal()
    try:
       beating = db.query(MatchPool).filter(MatchPool.user_id == user_id).first()
       if not beating:
           return {"msg": "user not in match pool"} 
       beating.last_heartbeat = datetime.now(timezone.utc)
       db.commit()
       return {"msg": "heartbeat updated"}
    finally:
        db.close()

@app.post("/match/{user_id}/leave")
def leave_match(user_id: int):
    db = SessionLocal()
    try:
        leaving = db.query(MatchPool).filter(MatchPool.user_id == user_id).first()
        if not leaving:
            return {"msg": "user not in match pool"}
        db.delete(leaving)
        db.commit()
        return {"msg": "left match pool"}
    finally:
        db.close()

@app.post("/match/match_users/{user_id}")
def match_users(user_id: int):
    db = SessionLocal()
    try:
        current_user = db.query(User).filter(User.id == user_id).first()
        if not current_user:
            return {"msg": "user not found"}

        matcher = db.query(MatchPool).filter(
            MatchPool.user_id != user_id,
            MatchPool.status == current_user.status,
            MatchPool.problem_type == current_user.problem_type,
            MatchPool.is_matched == False
        ).first()

        if not matcher:
            return {"match_type": "ai", "acc_user_id": None}

        matcher.is_matched = True
        db.commit()

        return {
            "match_type": "mentor",
            "acc_user_id": matcher.user_id,
            "req_user_id": current_user.id
        }

    finally:
        db.close()

@app.get("/match/release_mentor/{user_id}")
def release_mentor(user_id: int):
    db = SessionLocal()
    try:
        mentor = db.query(MatchPool).filter(MatchPool.user_id == user_id).first()
        if not mentor:
            return {"msg": "mentor not found in match pool"}
        mentor.is_matched = False
        db.commit()
        return {"msg": "mentor released"}
    finally:
        db.close()