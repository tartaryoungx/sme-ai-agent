from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import webhook, chat, shop, knowledge, auth  # ← เพิ่ม auth


app = FastAPI(title="SME AI Agent" , version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True
)

@app.get("/health" , tags=["System"])
def health_check():
    return {"status" : "ok"}

app.include_router(webhook.router)
app.include_router(chat.router)
app.include_router(shop.router)
app.include_router(knowledge.router)
app.add_api_router(auth.router)  # ← เพิ่ม router ของ auth