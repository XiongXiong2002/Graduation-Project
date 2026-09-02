from pathlib import Path

from fastapi import HTTPException, UploadFile

from tools.checkon_file import check_image_text
from tools.get_file_data import get_default_img
from tools.upload_file import upload_image


def save_approved_avatar(file: UploadFile | None):
    """检测并保存头像；没有上传时返回后端默认头像地址。"""

    if file is None:
        return get_default_img()

    try:
        if check_image_text(file):
            return upload_image(file)
    except HTTPException:
        raise
    except Exception as exc:
        # 服务器日志保留原始错误，方便排查。
        print(f"Avatar processing failed: {exc!r}")
        raise HTTPException(
            status_code=429,
            detail="picture not allowed",
        ) from exc

    return get_default_img()


def delete_stored_avatar(old_avatar: str | None,new_avatar: str,) :
    """数据库头像地址替换成功后，清理旧的用户上传文件。"""

    default_avatar = get_default_img()

    if ( old_avatar and old_avatar != new_avatar and old_avatar != default_avatar):
        img_dir = (Path(__file__).resolve().parent.parent / "img").resolve()
        old_path = (img_dir / Path(old_avatar).name).resolve()

        if old_path.parent == img_dir and old_path.is_file():
            try:
                old_path.unlink()
            except OSError as exc:
                # 删除旧头像失败不应该让已成功的资料更新返回 500。
                print(f"Failed to delete old avatar: {exc!r}")