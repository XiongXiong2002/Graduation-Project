import re
from rapidfuzz import fuzz


def normalize_programme(text: str) -> str:
    """
    规整专业名称：
    1. 处理空值
    2. 去掉前后空格
    3. 统一小写
    4. 删除空格和特殊符号
    5. 只保留英文字母和数字
    """

    if not text:
        return ""

    text = text.strip()
    text = text.lower()
    text = re.sub(r"[^a-z0-9]", "", text)

    return text


def calculate_programme_similarity(programme_a: str, programme_b: str) -> int:
    """
    计算两个专业名称的相似度。

    返回值范围：
    0 到 100

    数字越高，说明两个专业越相似。
    """

    a = normalize_programme(programme_a)
    b = normalize_programme(programme_b)

    # 如果任意一方为空，直接认为不相似
    if not a or not b:
        return 0

    # fuzz.ratio 会计算两个字符串的相似程度
    similarity = fuzz.ratio(a, b)

    return similarity


def programme_match_score(programme_a: str, programme_b: str) -> int:
    """
    把专业相似度转换成匹配分数。

    这个分数会被 matchRouter 用来给候选导师加权。
    """

    similarity = calculate_programme_similarity(
        programme_a,
        programme_b
    )
    if similarity < 50:
        return 0
    

    return similarity // 10  # 将相似度转换为 0-10 的分数    