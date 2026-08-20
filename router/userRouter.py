# standard library
from datetime import datetime, timezone
import json
from typing import Annotated

# third-party dependencies
from fastapi import APIRouter, Depends, Form, HTTPException

from sqlalchemy.exc import IntegrityError

# authentication
from auth import get_current_user

# database
from database import SessionLocal

# request schemas
from schames.block_info import BlockInfo
from schames.personalInfo import personalInfoRequest

# database tables
from tables.black_list import BlackList
from tables.user import User

# tools
from tools.get_file_data import (
    load_city_names,
    VALID_PROBLEM_TYPES,
    VALID_STATUSES,
    VALID_ACADEMIC_LEVELS,
    load_university_names,
)
from tools.avatar import delete_stored_avatar, save_approved_avatar


app = APIRouter()
VALID_UNIVERSITIES = load_university_names()
VALID_LOCATIONS = load_city_names()


@app.post("/user/update_profile")
def update_profile(
    # 头像上传修改（后端生成头像地址）：完整资料 schema 直接从 multipart FormData 读取。
    data: Annotated[personalInfoRequest, Form()],

    # =========================
    # FastAPI 自动认证
    #
    # 请求进入接口前，会先执行 get_current_user()
    # 如果 token 过期、无效，或者用户不存在，
    # FastAPI 会直接返回 401，下面的更新逻辑不会执行。
    # =========================
    current_user: User = Depends(get_current_user)
):
    db = SessionLocal()

    try:
        # =========================
        # 重新查询数据库中的用户
        #
        # current_user 已经通过认证存在；
        # 这里重新查询，是为了拿到可修改的 ORM 对象。
        # =========================
        user = db.query(User).filter(
            User.id == current_user.id
        ).first()

        if not user:
            return {
                "msg": "user not found"
            }

        # =========================
        # 先校验，再写入
        #
        # 避免出现前几个字段已经被改了，
        # 后面字段才发现不合法的半更新状态。
        # =========================
        if data.username is not None and not data.username.strip():
            return {
                "msg": "invalid username"
            }

        if data.status is not None and data.status not in VALID_STATUSES:
            return {
                "msg": "invalid status"
            }

        if data.problem_type is not None and data.problem_type not in VALID_PROBLEM_TYPES:
            return {
                "msg": "invalid problem type"
            }

        if data.academic_level is not None and data.academic_level not in VALID_ACADEMIC_LEVELS:
            return {
                "msg": "invalid academic level"
            }

 
        if data.institution is not None and data.institution not in VALID_UNIVERSITIES:
            return {
                "msg": "invalid institution"
            }

        if data.location is not None and data.location not in VALID_LOCATIONS:
            return {
                "msg": "invalid location"
            }

        if data.programme is not None and not data.programme.strip():
            return {
                "msg": "invalid programme"
            }
        
        # 沿用已有格言审核：长度不能超过 200 个字符。
        if data.motto is not None and len(data.motto)>200:
            return{
                "msg": "invalid motto"
            }

        # =========================
        # 更新用户基础资料
        # =========================
        if data.username is not None:
            user.username = data.username.strip()

        if data.status is not None:
            user.status = data.status

        if data.problem_type is not None:
            user.problem_type = data.problem_type

        if data.academic_level is not None:
            user.academic_level = data.academic_level



        if data.institution is not None:
            user.institution = data.institution

        if data.programme is not None:
            user.programme = data.programme.strip()

        if data.location is not None:
            user.location = data.location

        old_avatar = user.photo

        # 头像上传修改（后端生成头像地址）：有新文件才替换头像，否则保留数据库原地址。
        if data.img is not None:
            user.photo = save_approved_avatar(data.img)

        # 去掉格言两端的空格后再保存。
        if data.motto is not None:
            user.motto = data.motto.strip()



        db.commit()
        db.refresh(user)

        # 头像上传修改（后端生成头像地址）：资料提交成功后清理旧的用户上传文件。
        if data.img is not None:
            delete_stored_avatar(old_avatar, user.photo)

        return {
            "msg": "profile updated",

            "user_info": {
                "id": user.id,
                "username": user.username,
                "role": user.role,
                "status": user.status,
                "problem_type": user.problem_type,
                "academic_level": user.academic_level,
                "institution": user.institution,
                "programme": user.programme,
                "location": user.location,
                "img": user.photo,
                "motto": user.motto
            }
        }

    finally:
        db.close()


@app.get("/user/get_universities")
def get_universities():
    with open("data/uk_universities.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    return data


@app.get("/user/get_locations")
def get_locations():
    with open("data/uk_cities.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    return data


@app.get("/user/get_blacklist")
def get_blacklist(current_user: User = Depends(get_current_user)):
    db = SessionLocal()

    try:
        blacklist = db.query(BlackList).filter(
            BlackList.blocker_id == current_user.id
        ).all()

        return blacklist

    finally:
        db.close()

@app.post("/user/add_blacklist")
def add_blacklist(blockinfo: BlockInfo,current_user: User = Depends(get_current_user)):
    db =SessionLocal()
    try:
        # 禁止当前用户把自己加入自己的黑名单。
        if blockinfo.blocked_id == current_user.id:
            raise HTTPException(status_code=400, detail="you cannot block yourself")

        # 被拉黑的目标用户必须真实存在。
        blocked_user = db.query(User).filter(
            User.id == blockinfo.blocked_id
        ).first()

        if not blocked_user:
            raise HTTPException(status_code=400, detail="user not found")

        # 去掉理由两端空格；空字符串按没有填写理由处理。
        reason = blockinfo.reason.strip() if blockinfo.reason else None
        reason = reason or None

        # 与数据库 reason 字段的 VARCHAR(255) 长度保持一致。
        if reason and len(reason) > 255:
            raise HTTPException(status_code=400, detail="block reason must be 255 characters or fewer")

        # 已经拉黑过该用户时只更新理由，避免创建重复记录。
        existing = db.query(BlackList).filter(
            BlackList.blocker_id == current_user.id,
            BlackList.blocked_id == blockinfo.blocked_id,
        ).first()

        if existing:
            existing.reason = reason
            db.commit()
            return {"msg": "blacklist updated"}

        # blocker_id 使用 token 验证后的当前用户 ID，
        # 不信任前端提交的 blocker_id，防止冒充其他用户。
        newInfo = BlackList(
            blocker_id=current_user.id,
            blocked_id=blockinfo.blocked_id,
            reason=reason,
            # BlackList 模型没有默认值，因此创建时主动写入 UTC 时间。
            created_at=datetime.now(timezone.utc),
        )
        db.add(newInfo)
        db.commit()
        return {"msg": "user blocked"}
    
    # 数据库完整性错误发生后必须回滚事务。
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="user already blocked")

    finally:
        # 无论成功、提前返回还是抛出异常，都关闭数据库连接。
        db.close()

@app.post("/user/delete_blacklist")
def delete_blacklist( blockinfo: BlockInfo,current_user: User = Depends(get_current_user)):
    db = SessionLocal()

    try:
        # 不能把自己作为被删除的黑名单对象
        if current_user.id == blockinfo.blocked_id:
            raise HTTPException(status_code=400, detail="you cannot remove yourself from blacklist")

        # 只能查找由当前用户创建的黑名单记录
        rec = db.query(BlackList).filter( BlackList.blocker_id == current_user.id,BlackList.blocked_id == blockinfo.blocked_id).first()

        # 记录不存在，或者这条记录并不属于当前用户
        if not rec:
            raise HTTPException(status_code=404, detail="blacklist record not found")

        db.delete(rec)
        db.commit()
        return {
            "msg": "success"
        }

    except HTTPException:
        # HTTPException 不需要 rollback，因为没有数据库写入
        raise

    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="failed to remove user from blacklist")

    finally:
        db.close()

    







