# standard library
import json
from pathlib import Path


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


VALID_UNIVERSITIES = load_university_names()
VALID_CITIES = load_city_names()


VALID_STATUSES = {
    "current_student",
    "considering_withdrawal",
    "withdrawn",
    "graduate",
    "not_student",
}

VALID_PROBLEM_TYPES = {
    "academic",
    "stress",
    "interpersonal",
    "economic",
    "other",
}

# 用户只能选择这里列出的头像路径；注册和修改资料时都会再次校验。
VALID_IMG = {
    "/img/favicon.svg",
}
