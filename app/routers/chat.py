from fastapi import APIRouter, Depends
from pydantic import BaseModel
from app.ai.gemini import ask_gemini
from app.dependencies import verify_shop , verify_jwt_auth
from app.services.token_usage import log_token_usage

router = APIRouter(prefix="/api/v1" , tags=["Chat"])

class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None

@router.post("/chat")
async def chat(
    payload : ChatRequest ,
    shop_id: str = Depends(verify_shop) ,
    auth_data: dict = Depends(verify_jwt_auth)
):
    response = ask_gemini(payload.message, shop_id)

    log_token_usage(
        shop_id=shop_id,
        session_id=payload.session_id,
        model="gemini-2.5-flash-lite",
        usage=response["usage"]
    )
    #todo send message to langchain agent + prompt caching
    return {
        "shop_id" : shop_id ,
        "session_id": payload.session_id,
        "user": auth_data["sub"],
        "reply" : response["text"] ,
        "status": "success",
        "usage": response["usage"]
    }
