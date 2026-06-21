from database import SessionLocal
from schames.personalInfo import personalInfoRequest
from tables.user import User
from auth import get_current_user
from fastapi import APIRouter, Depends

app = APIRouter()


@app.post("/user/update_profile")
def update_profile(
    data: personalInfoRequest,

    # =========================
    # FastAPI 自动认证
    #
    # 执行流程：
    #
    # Authorization Header
    # ↓
    # get_current_user()
    # ↓
    # verify_token()
    # ↓
    # 检查签名
    # ↓
    # 检查 exp 是否过期
    # ↓
    # 查询数据库用户
    # ↓
    # 返回 current_user
    #
    # 如果：
    # - token 过期
    # - token 被篡改
    # - 用户不存在
    #
    # 会直接返回 401
    #
    # update_profile 根本不会执行
    # =========================
    current_user: User = Depends(get_current_user)
):
    print(data)

    db = SessionLocal()

    try:

        # =========================
        # 再次查询数据库中的用户
        #
        # current_user 本身已经存在
        #
        # 这里重新查询的目的：
        # 获取可修改的 ORM 对象
        # =========================
        user = db.query(User).filter(
            User.id == current_user.id
        ).first()

        # 理论上不会发生
        #
        # 因为 get_current_user()
        # 已经保证用户存在
        if not user:

            return {
                "msg": "user not found"
            }

        # =========================
        # 更新用户名
        # =========================
        if data.username is not None:

            user.username = data.username

        # =========================
        # 更新身份状态
        #
        # current_student
        # withdrawn_student
        # =========================
        if data.status is not None:

            user.status = data.status

        # =========================
        # 更新问题类型
        #
        # academic
        # financial
        # social
        # ...
        # =========================
        if data.problem_type is not None:

            user.problem_type = data.problem_type

        # =========================
        # 更新匹配偏好
        # =========================
        if data.preference is not None:

            user.preference = data.preference

        # =========================
        # 提交数据库修改
        # =========================
        db.commit()

        # =========================
        # 从数据库重新读取最新数据
        #
        # 保证返回给前端的是
        # 数据库中的最终结果
        # =========================
        db.refresh(user)

        # =========================
        # 返回最新用户信息
        #
        # 前端会更新 localStorage
        # =========================
        return {
            "msg": "profile updated",

            "user_info": {
                "id": user.id,
                "username": user.username,
                "role": user.role,
                "status": user.status,
                "problem_type": user.problem_type,
                "preference": user.preference
            }
        }

    finally:

        db.close()