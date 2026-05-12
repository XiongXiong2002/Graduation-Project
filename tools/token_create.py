import secrets


def generate_token(seeds: int = 32) -> str:

    # 生成安全随机 token
    #
    # token_urlsafe:
    # - 适合放 URL
    # - 不包含奇怪字符
    # - 安全性足够
    return secrets.token_urlsafe(seeds)