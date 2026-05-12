# 发送邮件相关
import smtplib

# 邮件内容格式
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# 环境变量
from dotenv import load_dotenv
import os

# 读取 .env
load_dotenv()

# 读取邮箱账号
MY_GMAIL = os.getenv("MY_GMAIL")
MY_PASSWORD = os.getenv("MY_PASSWORD")


# 定义发送邮件函数
def send_email(to_email, subject, body):

    # 创建邮件对象
    msg = MIMEMultipart()

    # 发件人
    msg["From"] = MY_GMAIL

    # 收件人
    msg["To"] = to_email

    # 邮件标题
    msg["Subject"] = subject

    # 邮件正文 pain 纯文本 或 html 网页格式
    msg.attach(MIMEText(body, "plain"))

    # 连接 Gmail SMTP 服务器
    server = smtplib.SMTP("smtp.gmail.com", 587)

    # 开启加密
    server.starttls()

    # 登录 Gmail
    server.login(MY_GMAIL, MY_PASSWORD)

    # 发送邮件
    server.send_message(msg)

    # 关闭连接
    server.quit()


# 测试发送
send_email(
    to_email="你自己的另一个邮箱@gmail.com",
    subject="Test Email",
    body="Hello World"
)