from io import BytesIO
from pathlib import Path
from tempfile import NamedTemporaryFile

from fastapi import HTTPException, UploadFile
from nudenet import NudeDetector
from PIL import Image, UnidentifiedImageError


import pytesseract
from detoxify import Detoxify



detector = NudeDetector()
detoxify_model = Detoxify("unbiased")


def check_image_text(file: UploadFile) -> bool:

    if file.content_type not in ["image/jpeg", "image/png"]:
        raise HTTPException(status_code=400, detail="Invalid file type. Only JPEG and PNG are allowed.")

    # 读取文件内容
    # 头像上传修改（后端生成头像地址）：先读取并限制大小，检测结束后再复位供保存函数使用。
    image_data = file.file.read()

    #检查文件大小
    if len(image_data) > 2 * 1024 * 1024:  # 2MB
        raise HTTPException(status_code=400, detail="File size exceeds the limit of 2MB.")

    try:
        # 头像上传修改（后端生成头像地址）：验证真实图片内容，不能只信任前端提供的 MIME 类型。
        Image.open(BytesIO(image_data)).verify()
    except (UnidentifiedImageError, OSError) as error:
        raise HTTPException(status_code=400, detail="Invalid image content.") from error


    # 头像上传修改（后端生成头像地址）：临时文件扩展名以后端确认过的 MIME 类型为准。
    suffix = ".jpg" if file.content_type == "image/jpeg" else ".png"
    temp_path = None

    try:
        # 头像上传修改（后端生成头像地址）：NudeDetector 接收文件路径，临时文件不会进入公开 img 目录。
        with NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
            temp_file.write(image_data)
            temp_path = Path(temp_file.name)

        detections = detector.detect(str(temp_path))
    finally:
        file.file.seek(0)
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)

    for item in detections:
        if (
            item["class"] in BLOCKED_CLASSES
            and item["score"] > 0.7
        ):
            return False


    # # OCR,此处等到部署在服务器上再启用，部署在本地时会报错
    text = pytesseract.image_to_string(
        Image.open(file.file)
    ).strip()

    # 图片没有文字
    if not text:
        return True

    # 检测文字
    result = detoxify_model.predict(text)

    if result["toxicity"] > 0.8:
        return False

    if result["threat"] > 0.7:
        return False

    if result["identity_attack"] > 0.7:
        return False

    return True


BLOCKED_CLASSES = {
    "FEMALE_BREAST_EXPOSED",
    "FEMALE_GENITALIA_EXPOSED",
    "MALE_GENITALIA_EXPOSED",
    "BUTTOCKS_EXPOSED",
    "ANUS_EXPOSED",
}





