# standard library
from pathlib import Path
from typing import Annotated, TypedDict

# third-party dependencies
from fastapi import APIRouter, Depends, Form, HTTPException, Response

# authentication
from auth import get_current_user

# database
from database import SessionLocal

# request schemas
from schames.mentor_verifiy_info import MentorVerifyInfo

# database tables
from tables.user import User

# password tools
from tools.password_hashed import verify_password


app = APIRouter()

ALLOWED_FILE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp"}
MAX_FILE_SIZE = 5 * 1024 * 1024


class UploadedVerificationFile(TypedDict):
    filename: str
    content_type: str
    content: bytes


# 人工审核凭证只暂存在当前进程内，审核完成或服务重启后不再保留。
uploaded_files: dict[int, UploadedVerificationFile] = {}


def require_admin(current_user: User) -> None:
    # 所有管理员接口统一在这里检查角色，避免各接口重复权限逻辑。
    if current_user.role != "admin":
        raise HTTPException(
            status_code=403,
            detail="Only admin can access this endpoint"
        )


def get_mentor(db, request_user_id: int) -> User:
    # 根据用户 ID 查找需要人工审核的 Mentor。
    user = db.query(User).filter(User.id == request_user_id).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.role != "mentor":
        raise HTTPException(status_code=400, detail="User is not a mentor")

    return user


@app.post("/user/upload_verification_file")
def upload_verification_file(mentor_verify_info: Annotated[MentorVerifyInfo, Form()]):
    # 从完整 FormData schema 中读取人工审核凭证。
    uploaded_file = mentor_verify_info.uploaded_file
    suffix = Path(uploaded_file.filename or "").suffix.lower()

    # 人工审核凭证只接受常用图片格式。
    if suffix not in ALLOWED_FILE_SUFFIXES:
        raise HTTPException(status_code=400, detail="Unsupported image format")

    content = uploaded_file.file.read()

    # 拒绝空文件以及超过 5MB 的文件。
    if not content or len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="Invalid file size")

    db = SessionLocal()

    try:
        # 使用注册邮箱定位账号，再验证密码，防止冒用其他 Mentor 身份上传。
        user = db.query(User).filter(
            User.email == mentor_verify_info.account_email
        ).first()

        if (
            not user
            or not verify_password(
                mentor_verify_info.account_password,
                user.password_hash
            )
        ):
            raise HTTPException(status_code=401, detail="Invalid account credentials")

        if user.role != "mentor":
            raise HTTPException(status_code=400, detail="User is not a mentor")

        if not user.is_email_verified:
            raise HTTPException(status_code=400, detail="Account email not verified")

        if user.mentor_verify_status == "approve":
            return {"message": "Mentor already approved"}

        # 文件仅暂存在当前进程内，同时把 Mentor 状态改为审核中，存储文件内容，防止仅存储临时上传的file对象的话当fastapi关闭会导致文件丢失。
        uploaded_files[user.id] = {
            "filename": Path(uploaded_file.filename or "verification-file").name,
            "content_type": uploaded_file.content_type or "application/octet-stream",
            "content": content,
        }
        user.mentor_verify_status = "pending"
        db.commit()

        return {"message": "File uploaded successfully, verification pending"}

    finally:
        db.close()


@app.get("/admin/get_uploaded_file")
def get_uploaded_file(request_user_id: int, current_user: User = Depends(get_current_user)):
    # 管理员根据 Mentor 用户 ID 查看待审核凭证。
    require_admin(current_user)
    uploaded_file = uploaded_files.get(request_user_id)

    if not uploaded_file:
        raise HTTPException(status_code=404, detail="File not found")

    # 将内存中保存的图片字节直接作为 HTTP 响应返回给管理员。
    return Response(
        # 实际的图片二进制内容。
        content=uploaded_file["content"],
        # 告诉浏览器图片的 MIME 类型，例如 image/jpeg 或 image/png。
        media_type=uploaded_file["content_type"],
        headers={
            # inline 表示优先在浏览器中预览；filename 保留原文件名。
            "Content-Disposition": (
                f'inline; filename="{uploaded_file["filename"]}"'
            )
        }
    )


@app.get("/admin/get_all_pending_users")
def get_all_pending_users(current_user: User = Depends(get_current_user)):
    # 返回当前进程中所有等待人工审核的 Mentor 用户 ID。
    require_admin(current_user)
    return {"pending_users": list(uploaded_files.keys())}


@app.post("/admin/approve_mentor_verification")
def approve_mentor_verification(request_user_id: int, current_user: User = Depends(get_current_user)):
    # 只有管理员可以批准 Mentor 人工审核。
    require_admin(current_user)
    db = SessionLocal()

    try:
        user = get_mentor(db, request_user_id)

        if request_user_id not in uploaded_files:
            raise HTTPException(status_code=404, detail="Pending file not found")

        # 批准后更新数据库状态，并删除内存中的临时审核文件。
        user.mentor_verify_status = "approve"
        db.commit()
        uploaded_files.pop(request_user_id, None)

        return {"message": "Mentor verification approved"}

    finally:
        db.close()


@app.post("/admin/disapprove_mentor_verification")
def disapprove_mentor_verification(request_user_id: int, current_user: User = Depends(get_current_user)):
    # 只有管理员可以拒绝 Mentor 人工审核。
    require_admin(current_user)
    db = SessionLocal()

    try:
        user = get_mentor(db, request_user_id)
        # 拒绝后恢复未批准状态，并清理可能存在的临时审核文件。
        user.mentor_verify_status = "disapprove"
        db.commit()
        uploaded_files.pop(request_user_id, None)

        return {"message": "Mentor verification disapproved"}

    finally:
        db.close()
