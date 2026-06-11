from google import genai
from google.genai import types
from app.config import settings
import time

client = genai.Client(api_key=settings.GEMINI_API_KEY)

# เก็บ cache ต่อ shop { shop_id: (cache_name, expire_time) }
_cache_store: dict[str, tuple[str, float]] = {}

CACHE_TTL_SECONDS = 3600  # 1 ชั่วโมง

system_prompt = """คุณคือแอดมินขายสินค้า SME
กฎ:
- ตอบเป็นภาษาไทย
- ตอบไม่เกิน 3 ประโยค
- ถ้าถามเรื่องราคา ให้ตอบราคาโดยตรง
- ถ้าข้อมูลไม่พอ ให้ถามกลับ 1 คำถาม
- ห้ามเขียนเกิน 100 คำ
- น้ำเสียงเป็นธรรมชาติ เป็นมิตร และเน้นช่วยปิดการขาย
- ไม่ต้องใส่อีโมจิและสัญลักษณ์พิเศษใดๆ"""

def get_or_create_cache(shop_id: str, knowledge_base: str = "") -> str:
    """
    คืนค่า cache_name ของ shop
    ถ้า cache หมดอายุหรือไม่มี → สร้างใหม่
    """
    now = time.time()
    
    # เช็คว่า cache ยังใช้ได้อยู่ไหม
    if shop_id in _cache_store:
        cache_name, expire_time = _cache_store[shop_id]
        if now < expire_time:
            print(f"CACHE HIT for shop {shop_id}: {cache_name}")
            return cache_name
    
    # สร้าง cache ใหม่
    content_to_cache = system_prompt
    if knowledge_base:
        content_to_cache += f"\n\nข้อมูลสินค้าของร้าน:\n{knowledge_base}"
    
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
    print(f"CACHE CREATED for shop {shop_id}: {cache.name}")
    return cache.name


def ask_with_cache(message: str, shop_id: str, history: list = None) -> dict:
    """
    เรียก Gemini โดยใช้ context cache แทน system prompt ปกติ
    """
    cache_name = get_or_create_cache(shop_id)
    
    # build messages จาก history + message ใหม่
    contents = []
    for msg in (history or []):
        contents.append(msg)  # HumanMessage / AIMessage จาก LangChain
    contents.append(types.Content(
        role="user",
        parts=[types.Part(text=message)]
    ))
    
    response = client.models.generate_content(
        model="gemini-2.5-flash-lite",
        contents=contents,
        config=types.GenerateContentConfig(
            cached_content=cache_name,
        )
    )
    
    usage = response.usage_metadata
    return {
        "text": response.text,
        "cached_tokens": usage.cached_content_token_count or 0,
        "input_tokens": usage.prompt_token_count or 0,
        "output_tokens": usage.candidates_token_count or 0,
    }