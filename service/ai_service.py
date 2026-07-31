# standard library
import json

# third-party dependencies
from dotenv import load_dotenv
from fastapi import HTTPException
from openai import OpenAI
from sqlalchemy.orm import Session

# database
from database import SessionLocal

# database tables
from tables.ai_reference import AIReference
from tables.ai_summary import AISummary
from tables.message import Message

# tools
from tools.get_file_data import VALID_PROBLEM_TYPES
from tools.prompt_for_help import prompt_for_reply
from tools.prompt_for_identify import prompt_for_identify
from tools.prompt_for_summary import prompt_for_summary
from tools.limit_quest import ai_rate_limiter


# 读取 .env
load_dotenv()

# 创建 OpenAI 客户端
client = OpenAI()


# 询问 AI 得到当前问题分类
def get_current_problem_type(current_session_id: int, current_user_msg: str, db: Session) :
    # 默认使用空字符串，确保 AI 分类失败时仍然可以安全返回
    history = ""

    try:
        # 使用顶级方法传入的 db，避免重复创建数据库会话
        recent_messages = get_closest_user_msg(current_session_id, db)

        # 拼接最近的对话记录
        history = build_conversation_history(recent_messages)

        # 生成分类提示词
        prompt = prompt_for_identify(current_user_msg, history)

        # AI 返回 JSON 字符串
        result_text = ask_ai(prompt)
        result_data = json.loads(result_text)
        problem_type = result_data["problem_type"]

        # 再次进行白名单验证
        if problem_type not in VALID_PROBLEM_TYPES:
            return "other", history

        return problem_type, history

    except (json.JSONDecodeError, KeyError, TypeError):
        # AI 返回的 JSON 格式或字段不正确
        return "other", history

    except Exception as error:
        raise RuntimeError("AI classification failed") from error


# 返回当前询问的 AI 结果
def ask_ai_result(current_user_id: int, current_session_id: int, current_user_msg: str):
    ai_rate_limiter.check(current_user_id)
    # 顶级方法负责创建并关闭本次请求使用的数据库会话
    db = SessionLocal()

    try:
        # 分类和后续查询复用当前 db
        problem_type, history = get_current_problem_type(
            current_session_id,
            current_user_msg,
            db,
        )

        # 获取用户摘要
        summary = (
            db.query(AISummary)
            .filter(AISummary.user_id == current_user_id)
            .first()
        )

        # 获取对应问题类型的知识资料
        references = (
            db.query(AIReference)
            .filter(AIReference.problem_type == problem_type)
            .all()
        )

        if not summary:
            raise HTTPException(status_code=400, detail="no such summary")

        if not references:
            raise HTTPException(status_code=400, detail="no such reference")

        reference_text = build_reference(references)

        ask_content = prompt_for_reply(
            current_user_msg,
            history,
            summary.content,
            reference_text,
        )

        result = ask_ai(ask_content)

        # 防止把空的 AI 回复返回给前端
        if not result:
            raise HTTPException(status_code=500, detail="AI returned an empty response")

        return result

    finally:
        # 无论请求成功或失败，都要释放数据库会话
        db.close()


def update_ai_summary( current_user_id: int, current_session_id: int,):
    # 顶层函数创建数据库会话，并负责最终关闭
    db = SessionLocal()


    try:
        # 获取当前用户已有的长期摘要
        summary = (
            db.query(AISummary)
            .filter(AISummary.user_id == current_user_id)
            .first()
        )

        if not summary:
            raise HTTPException(status_code=400, detail="no such summary")

        # 获取本次 session 的全部对话
        messages = (
            db.query(Message)
            .filter(Message.session_id == current_session_id)
            .order_by(Message.timestamp.asc())
            .all()
        )

        if not messages:
            raise HTTPException(status_code=400, detail="no messages in this session")

        # 将 ORM 消息列表转换为 Prompt 可用的对话文本
        session_history = build_conversation_history(messages)

        # 使用旧摘要和本次完整对话生成新摘要
        prompt = prompt_for_summary( summary.content, session_history)

        new_content = ask_ai(prompt)

        if not new_content or not new_content.strip():
            raise HTTPException(status_code=500, detail="AI returned an empty summary")

        # 更新摘要
        summary.content = new_content.strip()

        db.commit()
        db.refresh(summary)

        return summary

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


def build_reference(references: list[AIReference]) :
    # 先加入参考资料的使用规则，限制 AI 只能依据给定资料回答
    reference_text = """
    The following knowledge summaries were manually curated from trusted student-support resources.

    Each summary includes its original source.

    They are summaries rather than complete source documents.

    Use them as supporting guidance when they are relevant to the student's situation.
    Do not assume every summary is applicable.
    Do not invent information beyond these summaries.

    """

    # 把每一条参考资料依次拼接到提示词中
    for reference in references:
        reference_text += (
            f"Topic: {reference.title}\n"
            f"Writer: {reference.writer}\n"
            f"Knowledge Summary:\n"
            f"{reference.content}\n\n"
            f"source:{reference.source}"
        )

    return reference_text


# 返回当前 session 最近的 10 条对话
def get_closest_user_msg(current_session_id: int, db: Session) :
    # 先按时间倒序查询，保证数据库只读取最近的 10 条消息
    closest_user_msg = (
        db.query(Message)
        .filter(Message.session_id == current_session_id)
        .order_by(Message.timestamp.desc())
        .limit(10)
        .all()
    )

    # 恢复为从旧到新的顺序，方便 AI 理解对话过程
    closest_user_msg.reverse()
    return closest_user_msg


# 询问 AI
def ask_ai(message: str) :
    # 使用 Responses API 发送提示词
    response = client.responses.create( model="gpt-5.6-luna", input=message,)

    # 只返回模型生成的文本内容
    return response.output_text


def build_conversation_history(messages: list[Message]) :
    # 把消息对象转换为 AI 提示词使用的对话文本
    history = ""

    for msg in messages:
        # sender_id 为空表示这条消息由 AI 发送
        if msg.sender_id is None:
            role = "AI"
        else:
            role = "User"

        # 每条消息独占一行，保留角色和内容
        history += f"{role}: {msg.content}\n"

    return history
