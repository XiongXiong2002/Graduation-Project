# standard library
import json
from pathlib import Path
import re

from fastapi import HTTPException


# 当前项目根目录
BASE_DIR = Path(__file__).resolve().parent.parent

UNIVERSITY_FILE = BASE_DIR / "data" / "uk_universities.json"
CITY_FILE = BASE_DIR / "data" / "uk_cities.json"


def load_university_names() -> set[str]:
    """
    从大学 JSON 文件中读取所有合法学校名称。

    使用 set：
    - 查询速度更快
    - 自动去重
    """
    with UNIVERSITY_FILE.open("r", encoding="utf-8") as file:
        universities = json.load(file)

    return {
        university["name"].strip()
        for university in universities
        if university.get("name")
    }


def load_city_names() -> set[str]:
    """
    从城市 JSON 文件中读取所有合法城市名称。
    """
    with CITY_FILE.open("r", encoding="utf-8") as file:
        cities = json.load(file)

    return {
        city.strip()
        for city in cities
        if isinstance(city, str) and city.strip()
    }


def load_university_dict() -> dict[str, set[str]]:
    """
    启动时读取大学 JSON，
    转换为：

    {
        "imperial college london": {
            "@ic.ac.uk",
            "@imperial.ac.uk"
        }
    }
    """

    with UNIVERSITY_FILE.open("r", encoding="utf-8") as file:
        universities = json.load(file)

    return {
        item["name"].strip().lower(): {
            domain.strip().lower()
            for domain in item.get("domains", [])
            if isinstance(domain, str) and domain.strip()
        }
        for item in universities
        if item.get("name")
    }


# =========================
# 只在模块第一次加载时执行一次
# =========================
UNIVERSITY_DOMAINS = load_university_dict()


VALID_UNIVERSITIES = load_university_names()
VALID_CITIES = load_city_names()


def verify_mentor_email( university_name: str, email: str) -> bool:

    """
    验证导师邮箱是否属于指定学校。
    """

    # 学校名字统一小写
    university_name = university_name.strip().lower()

    # 查这个学校
    domains = UNIVERSITY_DOMAINS.get(university_name)

    if not domains:
        raise HTTPException(status_code=403,detail="there is no valid email for this university")

    # 从邮箱中提取 @ 后缀
    match = re.search(r"@[^@\s]+$", email.strip().lower())

    if not match:
        raise HTTPException(status_code=403,detail="invalid email format")

    email_domain = match.group()
    if email_domain not in domains:
        raise HTTPException(status_code=403,detail="invalid university email")

    return True

VALID_STATUSES = {
    "current_student",
    "considering_withdrawal",
    "decided_to_withdraw",
    "withdrawn",
}

VALID_ACADEMIC_LEVELS = {1, 2, 3, 4}

VALID_PROBLEM_TYPES = {
    "academic",
    "stress",
    "interpersonal",
    "economic",
    "other",
}

def get_default_img() -> str:
    """返回后端 img 目录中的默认图标地址。"""
    # 头像上传修改（后端生成头像地址）：默认头像地址完全由后端目录生成，前端不自行指定地址。
    img_dir = BASE_DIR / "img"
    supported_suffixes = {".svg", ".jpg", ".jpeg", ".png", ".webp"}
    default_images = sorted(
        path for path in img_dir.iterdir()
        if path.is_file() and path.suffix.lower() in supported_suffixes
    )

    if not default_images:
        raise HTTPException(status_code=500, detail="default avatar not found")

    # 头像上传修改（后端生成头像地址）：优先选择 SVG 图标，避免随机命名的用户上传图成为默认头像。
    default_icon = next(
        (path for path in default_images if path.suffix.lower() == ".svg"),
        default_images[0]
    )
    return f"/img/{default_icon.name}"
