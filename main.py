# third-party dependencies
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

# 导入各个 router
# routers
from router.authRouter import app as auth_router
from router.chatRouter import app as chat_router
from router.matchRouter import app as match_router
from router.sessionRouter import app as session_router
from router.userRouter import app as user_router

# database initialization
from init_db import init_db

init_db()


# 创建 FastAPI 应用
app = FastAPI()

# 将项目 img 目录挂载为静态资源目录，导师展示页可按已保存的图片路径读取头像。
app.mount("/img", StaticFiles(directory="img"), name="img")


# =========================
# 配置 CORS
# =========================
# MVP 阶段直接全部开放
# 前后端分离开发时避免跨域问题
app.add_middleware(
    CORSMiddleware,

    # 允许所有来源访问
    allow_origins=["*"],

    # 允许携带 cookie / authorization
    allow_credentials=True,

    # 允许所有 HTTP 方法
    allow_methods=["*"],

    # 允许所有 headers
    allow_headers=["*"],
)


# =========================
# 注册路由
# =========================
app.include_router(user_router)
app.include_router(session_router)
app.include_router(chat_router)
app.include_router(match_router)
app.include_router(auth_router)

# =========================
# 测试接口
# =========================
@app.get("/")
def read_root():
    return {"message": "server running"}
