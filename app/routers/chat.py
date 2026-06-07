from fastapi import APIRouter, Depends
from pydantic import BaseModel
from app.dependencies import verify_shop , verify_jwt_auth

router = APIRouter(prefix="/api/v1" , tags=["Chat"])

class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None

@router.post("/chat")
async def chat_endpoint(
    payload : ChatRequest ,
    shop_id: str = Depends(verify_shop) ,
    auth_data: dict = Depends(verify_jwt_auth)
):
    
    #todo send message to langchain agent + prompt caching
    return {
        "shop_id" : shop_id ,
        "reply" : f"ระบบได้รับข้อความของคุณ: {payload.message}" , 
        "status" : "processing"
    }
