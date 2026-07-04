from database import SessionLocal
from tables.user import User
from tables.matchPool import MatchPool
from fastapi import Depends, APIRouter
from auth import get_current_user
from sqlalchemy.exc import IntegrityError
from tables.sessions import Session
from tools.programme_similarity import programme_match_score

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

            problem_type=current_user.problem_type,

            institution=current_user.institution,

            location=current_user.location,

            programme=current_user.programme
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

    # =========================
    # 获取当前学生信息
    # =========================
    current_user = db.query(User).filter(
        User.id == user_id
    ).first()

    # 用户不存在
    if not current_user:

        return {
            "match_type": "error",
            "msg": "user not found"
        }

    # =========================
    # 第一层硬筛选
    #
    # 仅寻找：
    # - 相同身份
    # - 相同问题类型
    #
    # MatchPool 保存的是导师加入匹配池时
    # 的资料快照
    # =========================
    candidates = db.query(MatchPool).filter(
        MatchPool.status == current_user.status,
        MatchPool.problem_type == current_user.problem_type
    ).all()

    # 没有符合条件的导师
    if not candidates:

        return {
            "match_type": "none"
        }

    # 当前最佳导师
    best_candidate = None

    # 当前最高分
    best_score = -1

    # =========================
    # 第二层加权评分
    #
    # 学校：+4
    # 地区：+1
    # 专业：programme_match_score()
    # =========================
    for candidate in candidates:

        # =========================
        # 理论保险
        #
        # 如果导师已经进入聊天
        # 不参与新的匹配
        # =========================
        open_session = db.query(Session).filter(
            (
                (Session.req_user_id == candidate.mentor_id) |
                (Session.acc_user_id == candidate.mentor_id)
            ) &
            (Session.state == "open")
        ).first()

        if open_session:
            continue

        score = 0

        # -------------------------
        # 同学校
        # -------------------------
        if candidate.institution == current_user.institution:

            score += 4

        # -------------------------
        # 同地区
        # -------------------------
        if candidate.location == current_user.location:

            score += 1

        # -------------------------
        # 专业相似度
        # -------------------------
        score += programme_match_score(
            current_user.programme,
            candidate.programme
        )

        # -------------------------
        # 更新最佳导师
        # -------------------------
        if score > best_score:

            best_score = score
            best_candidate = candidate

    # =========================
    # 所有导师均不可匹配
    # =========================
    if not best_candidate:

        return {
            "match_type": "none"
        }

    # =========================
    # 返回最佳导师
    #
    # MatchPool 中保存的是 mentor_id
    # =========================
    return {
        "match_type": "mentor",
        "acc_user_id": best_candidate.mentor_id
    }