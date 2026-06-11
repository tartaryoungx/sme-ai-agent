from fastapi import APIRouter, Request, BackgroundTasks
from app.config import settings
import requests
from app.ai.gemini import ask_gemini

router = APIRouter(prefix="/webhook" , tags=["webhook"])

@router.post("/line")
async def line_webhook(request: Request , background_tasks : BackgroundTasks):

    data = await request.json()
    signature = request.headers.get("X-Line-Signature")
    #print(type(data))
    #print("events",data["events"][0]["message"].keys())
    #print("event", data["events"])

    for event in data["events"]:
        if event["type"] == "message":
            reply_token = event["replyToken"]
            text = event["message"]["text"]
            print(f"Received message: {text}")
            print(event.keys())

            response = ask_gemini(text)

            requests.post(
                "https://api.line.me/v2/bot/message/reply",
                headers={
                    "Authorization": f"Bearer {settings.LINE_CHANNEL_ACCESS_TOKEN}",
                    "Content-Type": "application/json",
                },
                json={
                    "replyToken": reply_token,
                    "messages": [{"type": "text", "text":  response["text"]}],
                },
            )

    #todo ai engineer implemnent ai agent to process the webhook data and perform necessary actions in the background

    return {"message" : "success"}




