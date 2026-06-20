from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from jose import jwt
from datetime import datetime, timedelta, timezone
from app.database import supabase
from app.config import settings
import bcrypt

router = APIRouter(prefix="/api/v1/auth", tags=["Auth"])

class RegisterRequest(BaseModel):
    email: str
    password: str
    shop_id: str

class LoginRequest(BaseModel):
    email: str
    password: str

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))

def create_token(user_id: str, shop_id: str) -> str:
    payload = {
        "sub": user_id,
        "shop_id": shop_id,
        "exp": datetime.now(timezone.utc) + timedelta(days=7)
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.ALGORITHM)

@router.post("/register")
async def register(payload: RegisterRequest):
    existing = supabase.table("users")\
        .select("id")\
        .eq("email", payload.email)\
        .execute()
    
    if existing.data:
        raise HTTPException(status_code=400, detail="Email already registered")

    shop = supabase.table("shops")\
        .select("id")\
        .eq("id", payload.shop_id)\
        .execute()
    
    if not shop.data:
        raise HTTPException(status_code=404, detail="Shop not found")

    hashed = hash_password(payload.password)
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
    result = supabase.table("users")\
        .select("id, shop_id, password_hash")\
        .eq("email", payload.email)\
        .single()\
        .execute()

    if not result.data:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    user = result.data

    if not verify_password(payload.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = create_token(user["id"], user["shop_id"])

    return {
        "access_token": token,
        "token_type": "bearer",
        "shop_id": user["shop_id"]
    }