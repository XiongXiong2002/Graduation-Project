from datetime import datetime, timezone
from tables.user import User
from database import SessionLocal

from fastapi import APIRouter

app = APIRouter()
# matchRouter.py
online_users = set()        # 当前在匹配池的人
matched_users = set()       # 已经匹配中的人（防止重复匹配）

@app.post("/match/join")
def join(user_id: int):
    online_users.add(user_id)
    return {"msg": "joined"}


@app.post("/match/leave")
def leave(user_id: int):
    online_users.discard(user_id)
    matched_users.discard(user_id)
    return {"msg": "left"}

@app.post("/match/{user_id}")
def match(user_id: int):
    db = SessionLocal()
    try:
        # =========================
        # 1. 获取当前用户（一般是学生）
        # =========================
        current_user = db.query(User).filter(User.id == user_id).first()

        # 如果用户不存在，直接返回
        if not current_user:
            return {"msg": "user not found"}

        # =========================
        # 2. 遍历当前在线匹配池
        # online_users 是一个 set，存的是正在等待匹配的人
        # =========================
        for candidate_id in online_users:

            # -------------------------
            # 2.1 跳过自己（防止自己匹配自己）
            # -------------------------
            if candidate_id == user_id:
                continue

            # -------------------------
            # 2.2 跳过已经在匹配中的人
            # matched_users 是“锁”，防止重复匹配
            # -------------------------
            if candidate_id in matched_users:
                continue

            # -------------------------
            # 2.3 查询候选人信息（数据库）
            # -------------------------
            candidate = db.query(User).filter(User.id == candidate_id).first()

            # 如果查不到（极端情况），跳过
            if not candidate:
                continue

            # =========================
            # 3. 判断是否满足匹配条件
            # =========================
            if (
                candidate.role == "mentor"                     # 必须是导师
                and candidate.status == current_user.status    # 状态一致
                and candidate.problem_type == current_user.problem_type  # 问题类型一致
            ):
                # =========================
                # 4. 锁定双方（防止并发重复匹配）
                # =========================
                matched_users.add(candidate_id)
                matched_users.add(user_id)

                # =========================
                # 5. 从匹配池中移除双方（避免再次匹配）
                # =========================
                online_users.discard(candidate_id)
                online_users.discard(user_id)

                # =========================
                # 6. 返回匹配成功结果
                # =========================
                return {
                    "match_type": "mentor",
                    "acc_user_id": candidate_id
                }

        # =========================
        # 7. 如果没有找到导师 → fallback 到 AI
        # =========================
        return {
            "match_type": "ai",
            "acc_user_id": None
        }

    finally:
        # =========================
        # 8. 关闭数据库连接（防止泄露）
        # =========================
        db.close()