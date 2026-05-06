from datetime import datetime, timezone
from tables.user import User
from database import SessionLocal
from fastapi import Depends
from fastapi import HTTPException
from auth import get_current_user
from fastapi import APIRouter

app = APIRouter()
# matchRouter.py
online_users = set()        # 当前在匹配池的人
matched_users = set()       # 已经匹配中的人（防止重复匹配）

@app.post("/match/join")
def join(current_user: User = Depends(get_current_user)):

    # 防重复加入
    if current_user.id in online_users:
        return {"msg": "already in pool"}

    # 清理旧匹配状态（非常关键）
    matched_users.discard(current_user.id)

    online_users.add(current_user.id)

    return {"msg": "joined"}

@app.post("/match/leave")
def leave(current_user: User = Depends(get_current_user)):

    online_users.discard(current_user.id)
    matched_users.discard(current_user.id)

    return {"msg": "left"}

def find_match_for_user(user_id: int, db):
    current_user = db.query(User).filter(User.id == user_id).first()

    if not current_user:
        return {"match_type": "error", "msg": "user not found"}

    for candidate_id in list(online_users):
        if candidate_id == user_id:
            continue

        if candidate_id in matched_users:
            continue

        candidate = db.query(User).filter(User.id == candidate_id).first()

        if not candidate:
            continue

        if (
            candidate.role == "mentor"
            and candidate.status == current_user.status
            and candidate.problem_type == current_user.problem_type
        ):
            matched_users.add(candidate_id)
            matched_users.add(user_id)

            online_users.discard(candidate_id)
            online_users.discard(user_id)

            return {
                "match_type": "mentor",
                "acc_user_id": candidate_id
            }

    return {
        "match_type": "none",
        "acc_user_id": None,
        "msg": "no mentor available"
    }