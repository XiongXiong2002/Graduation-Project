from pathlib import Path

from fastapi import UploadFile

from tools.checkon_file import check_image_text
from tools.get_file_data import get_default_img
from tools.upload_file import upload_image


def save_approved_avatar(file: UploadFile | None) -> str:
    """检测并保存头像；没有上传或检测不通过时返回后端默认头像地址。"""
    # 头像上传修改（后端生成头像地址）：只有检测成功的图片才写入 img，其他情况返回后端默认图标地址。
    if file is None:
        return get_default_img()

    try:
        if check_image_text(file):
            return upload_image(file)
    except Exception:
        # 头像上传修改（后端生成头像地址）：格式、大小或检测异常时不保存上传内容，改用默认头像地址。
        pass

    return get_default_img()


def delete_stored_avatar(old_avatar: str | None, new_avatar: str) -> None:
    """数据库头像地址替换成功后，清理旧的用户上传文件。"""
    if old_avatar and old_avatar != new_avatar and old_avatar != get_default_img():
        img_dir = (Path(__file__).resolve().parent.parent / "img").resolve()
        old_path = (img_dir / Path(old_avatar).name).resolve()

        # 头像上传修改（后端生成头像地址）：只删除 img 目录内的旧用户文件，后端默认图标永远保留。
        if old_path.parent == img_dir and old_path.is_file():
            old_path.unlink()
