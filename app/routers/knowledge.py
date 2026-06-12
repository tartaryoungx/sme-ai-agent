from fastapi import APIRouter, Depends, BackgroundTasks
from pydantic import BaseModel
from app.database import supabase
from app.dependencies import verify_jwt_auth
from app.ai.rag import add_doc

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
    background_tasks: BackgroundTasks,
    auth: dict = Depends(verify_jwt_auth)
):
    result = supabase.table("products").insert({
        "shop_id": shop_id,
        **payload.model_dump()
    }).execute()

    # index ลง RAG ใน background — ไม่ทำให้ response ช้า
    stock_status = f"มีสินค้า {payload.stock} ชิ้น" if payload.stock > 0 else "สินค้าหมด"
    doc_text = (
        f"สินค้า: {payload.name}\n"
        f"รายละเอียด: {payload.description or '-'}\n"
        f"ราคา: {payload.price} บาท\n"
        f"สถานะ: {stock_status}"
    )
    background_tasks.add_task(add_doc, shop_id, doc_text)

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
    background_tasks: BackgroundTasks,
    auth: dict = Depends(verify_jwt_auth)
):
    result = supabase.table("faqs").insert({
        "shop_id": shop_id,
        **payload.model_dump()
    }).execute()

    # index ลง RAG ใน background
    doc_text = f"คำถาม: {payload.question}\nคำตอบ: {payload.answer}"
    background_tasks.add_task(add_doc, shop_id, doc_text)

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
    about: str | None = None
    custom_instructions: str | None = None

@router.put("/policy/{shop_id}")
async def update_policy(
    shop_id: str,
    payload: PolicyUpdate,
    background_tasks: BackgroundTasks,
    auth: dict = Depends(verify_jwt_auth)
):
    existing = supabase.table("shop_policies")\
        .select("id")\
        .eq("shop_id", shop_id)\
        .execute()

    if existing.data:
        supabase.table("shop_policies")\
            .update(payload.model_dump(exclude_none=True))\
            .eq("shop_id", shop_id)\
            .execute()
    else:
        supabase.table("shop_policies")\
            .insert({"shop_id": shop_id, **payload.model_dump(exclude_none=True)})\
            .execute()

    # index นโยบายลง RAG ใน background
    parts = []
    if payload.shipping_policy:
        parts.append(f"นโยบายการจัดส่ง: {payload.shipping_policy}")
    if payload.return_policy:
        parts.append(f"นโยบายการคืนสินค้า: {payload.return_policy}")
    if payload.payment_methods:
        parts.append(f"ช่องทางชำระเงิน: {payload.payment_methods}")
    if payload.business_hours:
        parts.append(f"เวลาทำการ: {payload.business_hours}")
    if payload.about:
        parts.append(f"ข้อมูลร้าน: {payload.about}")
    if payload.custom_instructions:
        parts.append(f"ข้อมูลเพิ่มเติม: {payload.custom_instructions}")
    if parts:
        background_tasks.add_task(add_doc, shop_id, "\n".join(parts))

@router.get("/policy/{shop_id}")
async def get_policy(shop_id: str):
    result = supabase.table("shop_policies")\
        .select("*")\
        .eq("shop_id", shop_id)\
        .single()\
        .execute()
    return result.data