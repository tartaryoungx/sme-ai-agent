from fastapi import APIRouter
from app.database import supabase

router = APIRouter(prefix="/shops", tags=["Shops"])

@router.post("")
async def create_shop(name: str):

    result = supabase.table("shops").insert({
        "name": name
    }).execute()

    return result.data

@router.get("")
async def list_shops():

    result = supabase.table("shops").select("*").execute()

    return result.data

@router.get("/{shop_name}")
async def get_shop(shop_name: str):
    result = supabase.table("shops").select("*").eq("name", shop_name).execute()
    return result.data