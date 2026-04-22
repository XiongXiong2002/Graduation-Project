from database import SessionLocal
from schames.login import loginRequest
from schames.personalInfo import personalInfoRequest
from schames.register import registerRequest
from tables.user import User
from tools.password_hashed import hash_password, verify_legal_password, verify_password
from fastapi import APIRouter

app = APIRouter()

@app.post("/user/login")
def login(user: loginRequest):
    db = SessionLocal()
    try:
        matched_user= db.query(User).filter(User.email == user.email).first()  
        if not matched_user:
            return {"msg": "invalid email or password"}
        if (verify_password(user.password, matched_user.password_hash)):
            return {"msg": "login successful",
                    "user_info": {
                        "id": matched_user.id,
                        "username": matched_user.username,
                        "email": matched_user.email,
                        "role": matched_user.role
                    }}
        else:
            return {"msg": "invalid email or password"}

    finally:
        db.close()

@app.post("/user/register")
def register(user: registerRequest):
    db = SessionLocal()
    try:
        existing_user = db.query(User).filter(User.email == user.email).first()
        if existing_user:
            return {"msg": "email already registered"}
        
        if not verify_legal_password(user.password) :
            return {"msg": "password must be at least 8 characters long"}

        new_user = User(
            username=user.username,
            email=user.email,
            password_hash=hash_password(user.password),
            role=user.role,
            status=user.status,
            problem_type=user.problem_type,
            preference=user.preference
        )
        db.add(new_user)
        db.commit()

        return {"msg": "registration successful"}
    finally:
        db.close()

@app.post("/user/update_profile")
def update_profile(user_id: int, data: personalInfoRequest):
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()

        if not user:
            return {"msg": "user not found"}

        if data.username is not None:
            user.username = data.username

        if data.status is not None:
            user.status = data.status

        if data.problem_type is not None:
            user.problem_type = data.problem_type

        if data.preference is not None:
            user.preference = data.preference

        db.commit()

        return {"msg": "profile updated"}

    finally:
        db.close()




@app.post("/user/update_password")
def update_password(user_id: int, user: registerRequest):pass
