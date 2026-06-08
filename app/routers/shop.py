from fastapi import APIRouter
from app.database import supabase

router = APIRouter(prefix="/shops", tags=["Shops"])

@router.post("")
async def create_shop(name: str):

    result = supabase.table("shops").insert({
        "name": name
    }).execute()

    return result.data