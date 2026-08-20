
from pathlib import Path
import shutil
from dotenv import load_dotenv
from fastapi import UploadFile
import os
import uuid



load_dotenv()
UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", "./img"))
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)



def upload_image(file: UploadFile) -> str:

  # 随机生成文件名
    # 头像上传修改（后端生成头像地址）：检测通过后才生成随机文件名并写入公开头像目录。
    suffix = {
        "image/jpeg": ".jpg",
        "image/png": ".png",
    }[file.content_type]
    filename = f"{uuid.uuid4()}{suffix}"

    # 最终保存路径
    file_path = UPLOAD_DIR / filename

    # 保存文件
    # 头像上传修改（后端生成头像地址）：检测过程读取过文件，因此保存前必须将文件指针复位。
    file.file.seek(0)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    return f"/img/{filename}"



