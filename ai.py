# third-party dependencies
from dotenv import load_dotenv
from openai import OpenAI

# 先读取 .env
load_dotenv()

# 再创建客户端
client = OpenAI()


def ask_ai(message: str) -> str:
    response = client.responses.create(
        model="gpt-5.6-luna",
        input=message,
    )

    return response.output_text


# 实际调用函数，并打印返回结果
reply = ask_ai("你好")
print(reply)
