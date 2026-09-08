# standard library
from datetime import datetime, timedelta, timezone

# third-party dependencies
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

# authentication
from auth import get_current_user

# database
from database import SessionLocal

# database tables
from tables.black_list import BlackList
from tables.matchPool import MatchPool
from tables.sessions import Session
from tables.user import User

# tools
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
            # 使用 403 明确表示用户已登录，但没有导师权限。
            raise HTTPException(status_code=403, detail="only mentor can join match pool")

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
                "msg": "You are already receiving matches. Please stop receiving before joining again."
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

            programme=current_user.programme,
            academic_level=current_user.academic_level
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
            "msg": "You are already receiving matches. Please stop receiving before joining again."
        }

    finally:

        db.close()

# =========================
# 检查当前导师是否在匹配池
# =========================
@app.get("/match/status")
def get_match_status(current_user: User = Depends(get_current_user)):
    if current_user.role != "mentor":
        raise HTTPException(status_code=403, detail="only mentor can check match status")
    db = SessionLocal()

    try:
        pool_item = db.query(MatchPool).filter(MatchPool.mentor_id == current_user.id).first()

        if pool_item:
            return {"msg": "in pool"}
        else:
            return {"msg": "not in pool"}
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

# 负责拿到所有的
@app.get("/match/find")
def find_match_for_user(current_user: User = Depends(get_current_user)):
    # 导师列表属于学生端功能，防止导师或其他角色直接调用接口。
    if current_user.role != "student":
        raise HTTPException(status_code=403, detail="only student can find mentors")

    db = SessionLocal()

    try:
        return _find_match_for_user(current_user, db)
    finally:
        db.close()


def _find_match_for_user(current_user: User, db):

    # =========================
    # 获取当前学生信息
    # =========================
    user_id = current_user.id
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
    # - 没被拉黑
    #
    # MatchPool 保存的是导师加入匹配池时
    # 的资料快照
    # =========================
    mentor_rows = (
        db.query(User, MatchPool)
        # 同时取得导师资料和对应的匹配池记录，
        # 便于硬筛选完成后检查心跳时间。
        .join(MatchPool, MatchPool.mentor_id == User.id)
        .filter(
            MatchPool.status == current_user.status,
            MatchPool.problem_type == current_user.problem_type,
            MatchPool.academic_level == current_user.academic_level,
            User.role == "mentor",
            User.id != current_user.id,
        )
        # 过滤掉被拉黑的导师
        .filter(
            ~User.id.in_(
                db.query(BlackList.blocked_id).filter(
                    BlackList.blocker_id == current_user.id
                )
            )
        )
        # 过滤掉拉黑当前学生的导师
        .filter(
            ~User.id.in_(
                db.query(BlackList.blocker_id).filter(
                    BlackList.blocked_id == current_user.id
                )
            )
        )
        .filter(
            # 过滤掉已经在聊天的导师
            ~User.id.in_(
                db.query(Session.acc_user_id).filter(
                    Session.state == "open",
                    # AI session 的 acc_user_id 为 NULL；必须排除 NULL，
                    # 否则 SQL 的 NOT IN 子查询可能把全部 Mentor 都过滤掉。
                    Session.acc_user_id.isnot(None)
                )
            )
        )
        .all()
    )

    # =========================
    # 心跳过期清理
    #
    # 上面的第一轮硬筛选全部完成后，
    # 再检查候选 Mentor 的最后心跳时间。
    # 超过一分钟未更新的记录：
    # 1. 从数据库 MatchPool 中删除；
    # 2. 不加入 mentors，因此也从本次返回列表排除。
    # =========================
    heartbeat_cutoff = datetime.now(timezone.utc) - timedelta(minutes=1)
    mentors = []

    for candidate, pool_item in mentor_rows:
        if pool_item.joined_at < heartbeat_cutoff:
            db.delete(pool_item)
            continue

        mentors.append(candidate)

    # 一次提交本轮所有过期匹配池记录的删除。
    db.commit()

    # 没有符合条件的导师
    if not mentors:

        return {
            "match_type": "none"
        }


    result =[]

    # =========================
    # 第二层加权评分
    #
    # 学校：+4
    # 地区：+1
    # 专业：programme_match_score()
    # =========================
    for candidate in mentors:

        # =========================
        # 理论保险
        #
        # 如果导师已经进入聊天
        # 不参与新的匹配
        # =========================
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
        # 给该导师添加分数
        # -------------------------
        result.append({
        "id": candidate.id,
        "username": candidate.username,
        "institution": candidate.institution,
        "programme": candidate.programme,
        "location": candidate.location,
        "status": candidate.status,
        "problem_type": candidate.problem_type,
        "academic_level": candidate.academic_level,
        # 头像上传修改（后端生成头像地址）：直接返回数据库中已经确定的导师头像地址。
        "img": candidate.photo,
        "motto": candidate.motto,
        "score": score,
    })
       


    # =========================
    # 排序后返回所有导师
    #
    # MatchPool 中保存的是 mentor_id
    # =========================
    # result 中保存的是字典，因此按字典里的 score 从高到低排序。
    result.sort(key=lambda x: x["score"], reverse=True)
    return {
        "match_type": "mentor",
        "all available mentors": result,
    }
