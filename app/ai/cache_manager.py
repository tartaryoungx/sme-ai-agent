from google import genai
from google.genai import types
from app.config import settings
from app.services.knowledge import build_knowledge_base
import time

client = genai.Client(api_key=settings.GEMINI_API_KEY)

_cache_store: dict[str, tuple[str, float]] = {}
CACHE_TTL_SECONDS = 3600

system_prompt = """คุณคือแอดมินขายสินค้า SME
กฎ:
- ตอบเป็นภาษาไทย
- ตอบไม่เกิน 3 ประโยค
- ถ้าถามเรื่องราคา ให้ตอบราคาโดยตรง
- ถ้าข้อมูลไม่พอ ให้ถามกลับ 1 คำถาม
- ห้ามเขียนเกิน 100 คำ
- น้ำเสียงเป็นธรรมชาติ เป็นมิตร และเน้นช่วยปิดการขาย
- ไม่ต้องใส่อีโมจิและสัญลักษณ์พิเศษใดๆ"""

def get_or_create_cache(shop_id: str) -> dict:
    """
    คืน dict เสมอ:
    - cache ได้  → {"cache_name": "...", "cached": True, "knowledge_base": "..."}
    - cache ไม่ได้ → {"cache_name": None, "cached": False, "knowledge_base": "...", "reason": "..."}
    """
    now = time.time()

    # cache ยังใช้ได้อยู่
    if shop_id in _cache_store:
        cache_name, expire_time = _cache_store[shop_id]
        if now < expire_time:
            print(f"[CACHE HIT] shop={shop_id}")
            return {"cache_name": cache_name, "cached": True, "knowledge_base": ""}

    knowledge_base = build_knowledge_base(shop_id)
    content_to_cache = system_prompt + "\n\nข้อมูลของร้าน:\n" + knowledge_base

    estimated_tokens = len(content_to_cache) // 2  # ภาษาไทย ~2 chars/token
    print(f"[CACHE] shop={shop_id} estimated_tokens={estimated_tokens}")

    # ไม่มีข้อมูลร้านเลย
    if not knowledge_base.strip():
        print(f"[CACHE SKIP] no knowledge base")
        return {
            "cache_name": None,
            "cached": False,
            "knowledge_base": "",
            "reason": "no_knowledge_base"
        }

    # ข้อมูลน้อยกว่า 2048 tokens
    if estimated_tokens < 2048:
        print(f"[CACHE SKIP] too small ~{estimated_tokens} tokens")
        return {
            "cache_name": None,
            "cached": False,
            "knowledge_base": knowledge_base,  # ← ส่ง knowledge_base กลับไปใช้ใน prompt แทน
            "reason": f"too_small_{estimated_tokens}_tokens"
        }

    # สร้าง cache ใหม่
    try:
        cache = client.caches.create(
            model="gemini-2.5-flash-lite",
            config=types.CreateCachedContentConfig(
                contents=[
                    types.Content(
                        role="user",
                        parts=[types.Part(text=content_to_cache)]
                    )
                ],
                ttl=f"{CACHE_TTL_SECONDS}s",
                display_name=f"shop-{shop_id}"
            )
        )
        _cache_store[shop_id] = (cache.name, now + CACHE_TTL_SECONDS - 60)
        print(f"[CACHE CREATED] shop={shop_id} cache={cache.name}")
        return {"cache_name": cache.name, "cached": True, "knowledge_base": ""}

    except Exception as e:
        print(f"[CACHE ERROR] {e}")
        return {
            "cache_name": None,
            "cached": False,
            "knowledge_base": knowledge_base,
            "reason": f"error_{str(e)}"
        }