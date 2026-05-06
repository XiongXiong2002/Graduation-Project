from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from router.userRouter import app as user_router
from router.sessionRouter import app as session_router
from router.chatRouter import app as chat_router
from router.matchRouter import app as match_router
from database import Base, engine
from tools.password_hashed import hash_password, verify_password, verify_legal_password

app = FastAPI()
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # MVP直接全开
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Base.metadata.create_all(bind=engine)

app.include_router(user_router) 
app.include_router(session_router)
app.include_router(chat_router)
app.include_router(match_router)    
@app.get("/")
def read_root():
    return {"message": "fuck your mama"}

