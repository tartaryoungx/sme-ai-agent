from fastapi import APIRouter, Depends
from pydantic import BaseModel
from app.ai.agent import ask_agent
from app.dependencies import verify_shop , verify_jwt_auth

router = APIRouter(prefix="/api/v1" , tags=["Chat"])

class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None

@router.post("/chat")
async def chat(
    payload: ChatRequest,
    shop_id: str = Depends(verify_shop),
    auth_data: dict = Depends(verify_jwt_auth)
):
    response = ask_agent(
        payload.message,
        shop_id=shop_id,
        user_id=auth_data.get("sub"),
        session_id=payload.session_id
    )
    return {
        "shop_id": shop_id,
        "session_id": response["session_id"],
        "user": auth_data["sub"],
        "reply": response["text"],
        "status": "success",
    }