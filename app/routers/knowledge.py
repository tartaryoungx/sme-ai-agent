from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from app.database import supabase
from app.dependencies import verify_jwt_auth

router = APIRouter(prefix="/api/v1/knowledge", tags=["Knowledge"])

# --- Products ---
class ProductCreate(BaseModel):
    name: str
    description: str | None = None
    price: float
    stock: int = 0

@router.post("/products")
async def create_product(
    shop_id: str,
    payload: ProductCreate,
    auth: dict = Depends(verify_jwt_auth)
):
    result = supabase.table("products").insert({
        "shop_id": shop_id,
        **payload.model_dump()
    }).execute()
    return result.data

@router.get("/products/{shop_id}")
async def list_products(shop_id: str):
    result = supabase.table("products")\
        .select("*")\
        .eq("shop_id", shop_id)\
        .eq("is_active", True)\
        .execute()
    return result.data

# --- FAQs ---
class FAQCreate(BaseModel):
    question: str
    answer: str

@router.post("/faqs")
async def create_faq(
    shop_id: str,
    payload: FAQCreate,
    auth: dict = Depends(verify_jwt_auth)
):
    result = supabase.table("faqs").insert({
        "shop_id": shop_id,
        **payload.model_dump()
    }).execute()
    return result.data

@router.get("/faqs/{shop_id}")
async def list_faqs(shop_id: str):
    result = supabase.table("faqs")\
        .select("*")\
        .eq("shop_id", shop_id)\
        .eq("is_active", True)\
        .execute()
    return result.data

# --- Policy ---
class PolicyUpdate(BaseModel):
    shipping_policy: str | None = None
    return_policy: str | None = None
    payment_methods: str | None = None
    business_hours: str | None = None
    about: str | None = None  # ← เพิ่ม
    custom_instructions: str | None = None  # ← เพิ่ม

@router.put("/policy/{shop_id}")
async def update_policy(
    shop_id: str,
    payload: PolicyUpdate,
    auth: dict = Depends(verify_jwt_auth)
):
    result = supabase.table("shop_policies")\
        .upsert({"shop_id": shop_id, **payload.model_dump(exclude_none=True)})\
        .execute()
    return result.data

@router.get("/policy/{shop_id}")
async def get_policy(shop_id: str):
    result = supabase.table("shop_policies")\
        .select("*")\
        .eq("shop_id", shop_id)\
        .single()\
        .execute()
    return result.data