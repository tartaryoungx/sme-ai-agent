from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from passlib.context import CryptContext
from jose import jwt
from datetime import datetime, timedelta
from app.database import supabase
from app.config import settings

router = APIRouter(prefix="/api/v1/auth", tags=["Auth"])

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class RegisterRequest(BaseModel):
    email: str
    password: str
    shop_id: str

class LoginRequest(BaseModel):
    email: str
    password: str

def create_token(user_id: str, shop_id: str) -> str:
    payload = {
        "sub": user_id,
        "shop_id": shop_id,
        "exp": datetime.utcnow() + timedelta(days=7)
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.ALGORITHM)

@router.post("/register")
async def register(payload: RegisterRequest):
    # เช็คว่า email ซ้ำไหม
    existing = supabase.table("users")\
        .select("id")\
        .eq("email", payload.email)\
        .execute()
    
    if existing.data:
        raise HTTPException(status_code=400, detail="Email already registered")

    # เช็คว่า shop มีอยู่จริง
    shop = supabase.table("shops")\
        .select("id")\
        .eq("id", payload.shop_id)\
        .execute()
    
    if not shop.data:
        raise HTTPException(status_code=404, detail="Shop not found")

    # hash password แล้วบันทึก
    hashed = pwd_context.hash(payload.password)
    result = supabase.table("users").insert({
        "email": payload.email,
        "password_hash": hashed,
        "shop_id": payload.shop_id,
    }).execute()

    user = result.data[0]
    token = create_token(user["id"], payload.shop_id)

    return {"access_token": token, "token_type": "bearer"}

@router.post("/login")
async def login(payload: LoginRequest):
    # หา user จาก email
    result = supabase.table("users")\
        .select("id, shop_id, password_hash")\
        .eq("email", payload.email)\
        .single()\
        .execute()

    if not result.data:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    user = result.data

    # เช็ค password
    if not pwd_context.verify(payload.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = create_token(user["id"], user["shop_id"])

    return {
        "access_token": token,
        "token_type": "bearer",
        "shop_id": user["shop_id"]
    }