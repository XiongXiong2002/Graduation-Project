from database import SessionLocal
from tables.user import User
from tables.matchPool import MatchPool
from fastapi import Depends, APIRouter
from auth import get_current_user
from sqlalchemy.exc import IntegrityError
from tables.sessions import Session

app = APIRouter()



@app.post("/match/join")
def join(current_user: User = Depends(get_current_user)):
    db = SessionLocal()

    try:

        # =========================
        # 只有导师允许加入匹配池
        # =========================
        if current_user.role != "mentor":

            return {
                "msg": "only mentor can join match pool"
            }

        # =========================
        # 检查是否已经存在 open session
        #
        # 防止：
        # - 导师正在聊天
        # - 用户修改前端
        # - 强行再次加入匹配池
        #
        # 如果存在 open session
        # 直接返回当前 session
        # =========================
        open_session = db.query(Session).filter(
            (
                (Session.req_user_id == current_user.id) |
                (Session.acc_user_id == current_user.id)
            ) &
            (Session.state == "open")
        ).first()

        if open_session:

            return {
                "msg": "you already have an open session",

                # 当前打开的 session
                "session_id": open_session.id
            }

        # =========================
        # 检查是否已经在匹配池
        #
        # 防止重复点击
        # =========================
        existing = db.query(MatchPool).filter(
            MatchPool.mentor_id == current_user.id
        ).first()

        if existing:

            return {
                "msg": "already in pool"
            }

        # =========================
        # 创建匹配池记录
        #
        # status:
        # current_student / withdrawn_student
        #
        # problem_type:
        # academic / financial / social ...
        #
        # 后续学生匹配时会根据这些字段筛选
        # =========================
        pool_item = MatchPool(
            mentor_id=current_user.id,

            status=current_user.status,

            problem_type=current_user.problem_type
        )

        # 写入数据库
        db.add(pool_item)

        db.commit()

        # =========================
        # 加入成功
        # =========================
        return {
            "msg": "joined"
        }

    # =========================
    # 数据库唯一约束保护
    #
    # 即使两个请求同时到达
    # 也不会产生两条记录
    # =========================
    except IntegrityError:

        db.rollback()

        return {
            "msg": "already in pool"
        }

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