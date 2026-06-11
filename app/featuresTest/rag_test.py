from fastapi import APIRouter
from app.ai.rag import add_doc, search_docs
from pydantic import BaseModel


router = APIRouter(prefix="/api/rag" , tags=["Rag"])

class RagRequest(BaseModel):
    content: str
    shop_id: str = "b5c79bc0-8e1b-46a7-a1d7-229b53f971de"


@router.post("/test")
async def test_rag(content: str, shop_id: str = "b5c79bc0-8e1b-46a7-a1d7-229b53f971de"):
    add_doc(shop_id, content)
    print(f"Added document for shop_id: {shop_id} with content: {content}")
    return {"message": "RAG test successful"}


@router.get("/search")
async def search_rag(shop_id: str, question: str):
    results = search_docs(shop_id, question)
    
    return {"results": results}
