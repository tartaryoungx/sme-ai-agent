import json
import traceback

from fastapi import HTTPException

from fastapi import APIRouter, Request, BackgroundTasks
import requests
from app.ai.agent import ask_agent 
import hmac, hashlib, base64
from app.database  import supabase

router = APIRouter(prefix="/webhook" , tags=["webhook"])

# function verify line signature
def verify_line_signature(body: bytes, signature: str, channel_secret: str) -> bool:
    hash = hmac.new(
        channel_secret.encode("utf-8"),
        body,
        hashlib.sha256
    ).digest()
    expected = base64.b64encode(hash).decode("utf-8")
    return hmac.compare_digest(expected, signature)

@router.post("/line/{shop_id}")
async def line_webhook(shop_id: str, request: Request, background_tasks: BackgroundTasks):
    result = supabase.table("shops")\
        .select("id, line_channel_secret, line_channel_access_token, is_active")\
        .eq("id", shop_id)\
        .single()\
        .execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Shop not found")

    shop = result.data

    if not shop["is_active"]:
        raise HTTPException(status_code=403, detail="Shop is not active")
    
    body = await request.body()
    signature = request.headers.get("X-Line-Signature", "")

    if not shop.get("line_channel_secret"):
        raise HTTPException(status_code=500, detail="Shop Line Channel Secret not configured")

    if not verify_line_signature(body, signature, shop["line_channel_secret"]):
        raise HTTPException(status_code=401, detail="Invalid signature")
    
    try:
        data = json.loads(body)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON body")
    
    for event in data.get("events", []):
        if event["type"] == "message" and event["message"]["type"] == "text":
            reply_token = event["replyToken"]
            text = event["message"]["text"]
            user_id = event["source"].get("userId")
            print(f"Received message: {text}")
            print(event.keys())

            try:
                response = ask_agent(
                    text,
                    shop_id=shop_id,
                    user_id=user_id,
                    session_id=user_id,
                )
                reply_text = response["text"]
            except Exception as e:
                print(f"[ERROR] ask_agent failed for shop={shop_id} user={user_id}")
                traceback.print_exc()
                reply_text = "ขออภัยครับ ระบบขัดข้องชั่วคราว กรุณาลองใหม่อีกครั้งนะครับ"

            if not shop.get("line_channel_access_token"):
                print(f"Error: Shop {shop_id} Line Channel Access Token not configured")
                continue

            try:
                requests.post(
                    "https://api.line.me/v2/bot/message/reply",
                    headers={
                        "Authorization": f"Bearer {shop['line_channel_access_token']}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "replyToken": reply_token,
                        "messages": [{"type": "text", "text": reply_text}],
                    },
                    timeout=10,
                )
            except Exception as e:
                print(f"[ERROR] LINE reply failed: {e}")
                traceback.print_exc()

    #todo ai engineer implemnent ai agent to process the webhook data and perform necessary actions in the background

    return {"message" : "success"}




