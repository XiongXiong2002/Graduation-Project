from database import SessionLocal
from tables.user import User
from tables.matchPool import MatchPool
from fastapi import Depends, APIRouter
from auth import get_current_user
from sqlalchemy.exc import IntegrityError

app = APIRouter()


@app.post("/match/join")
def join(current_user: User = Depends(get_current_user)):
    db = SessionLocal()

    try:
        if current_user.role != "mentor":
            return {"msg": "only mentor can join match pool"}

        existing = db.query(MatchPool).filter(
            MatchPool.mentor_id == current_user.id
        ).first()

        if existing:
            return {"msg": "already in pool"}

        pool_item = MatchPool(
            mentor_id=current_user.id,
            status=current_user.status,
            problem_type=current_user.problem_type
        )

        db.add(pool_item)
        db.commit()

        return {"msg": "joined"}

    except IntegrityError:
        db.rollback()
        return {"msg": "already in pool"}

    finally:
        db.close()


@app.post("/match/leave")
def leave(current_user: User = Depends(get_current_user)):
    db = SessionLocal()

    try:
        pool_item = db.query(MatchPool).filter(
            MatchPool.mentor_id == current_user.id
        ).first()

        if pool_item:
            db.delete(pool_item)
            db.commit()

        return {"msg": "left"}

    finally:
        db.close()


def find_match_for_user(user_id: int, db):
    current_user = db.query(User).filter(User.id == user_id).first()

    if not current_user:
        return {"match_type": "error", "msg": "user not found"}

    candidate = db.query(MatchPool).filter(
        MatchPool.status == current_user.status,
        MatchPool.problem_type == current_user.problem_type
    ).order_by(
        MatchPool.joined_at.asc()
    ).with_for_update(skip_locked=True).first()

    if not candidate:
        return {
            "match_type": "none",
            "acc_user_id": None,
            "msg": "no mentor available"
        }

    acc_user_id = candidate.mentor_id

    db.delete(candidate)

    return {
        "match_type": "mentor",
        "acc_user_id": acc_user_id
    }