# standard library
import base64
import json
import mimetypes
from datetime import datetime, timezone
from pathlib import Path

# third-party dependencies
from fastapi import APIRouter, Depends, HTTPException
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
    VALID_IMG,
    load_university_names,
)


app = APIRouter()
VALID_UNIVERSITIES = load_university_names()
VALID_LOCATIONS = load_city_names()


@app.post("/user/update_profile")
def update_profile(
    data: personalInfoRequest,

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
        
        # 修改头像时仍需验证路径属于合法头像白名单。
        if data.img is not None and data.img not in VALID_IMG :
            return{
                "msg": "invalid img"
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



        if data.institution is not None:
            user.institution = data.institution

        if data.programme is not None:
            user.programme = data.programme.strip()

        if data.location is not None:
            user.location = data.location

        # 前端提交的是选中头像的路径，数据库只保存该路径。
        if data.img is not None:
            user.photo = data.img

        # 去掉格言两端的空格后再保存。
        if data.motto is not None:
            user.motto = data.motto.strip()



        db.commit()
        db.refresh(user)

        return {
            "msg": "profile updated",

            "user_info": {
                "id": user.id,
                "username": user.username,
                "role": user.role,
                "status": user.status,
                "problem_type": user.problem_type,
                "institution": user.institution,
                "programme": user.programme,
                "location": user.location,
                # 返回最新头像路径和格言，供前端同步 localStorage。
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

    







@app.get("/user/get_img")
def get_img():
    # 返回合法头像的实际图片内容，同时保留图片路径。
    # 图片内容用于前端展示；图片路径用于用户提交资料时进行白名单校验。
    images = []

    for image_value in sorted(VALID_IMG):
        # VALID_IMG 中保存的是公开路径，例如 /img/favicon.svg。
        # 去掉开头的 / 后，转换为后端可以读取的本地文件路径。
        image_path = Path(image_value.lstrip("/"))
        mime_type = mimetypes.guess_type(image_path.name)[0] or "application/octet-stream"

        # JSON 不能直接保存二进制数据，因此先将图片字节编码为 Base64 字符串。
        encoded = base64.b64encode(image_path.read_bytes()).decode("ascii")

        images.append({
            # path 会在注册或修改资料时传回后端，并由 VALID_IMG 再次验证。
            "path": image_value,
            # mime_type 告诉前端如何还原图片类型。
            "mime_type": mime_type,
            # content_base64 是实际图片内容，不是图片访问地址。
            "content_base64": encoded,
        })

    return images
