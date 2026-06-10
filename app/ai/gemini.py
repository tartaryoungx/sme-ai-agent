
from google import genai
from google.genai import types
from app.config import settings
from langfuse import Langfuse
from langfuse import Langfuse, propagate_attributes

client = genai.Client(api_key=settings.GEMINI_API_KEY)

langfuse = Langfuse(
    public_key=settings.LANGFUSE_PUBLIC_KEY,
    secret_key=settings.LANGFUSE_SECRET_KEY,
    base_url=settings.LANGFUSE_BASE_URL,
)

print(langfuse.auth_check())


system_prompt = """คุณคือแอดมินขายสินค้า SME
กฎ:
- ตอบเป็นภาษาไทย
- ตอบไม่เกิน 3 ประโยค
- ถ้าถามเรื่องราคา ให้ตอบราคาโดยตรง
- ถ้าข้อมูลไม่พอ ให้ถามกลับ 1 คำถาม
- ห้ามเขียนเกิน 100 คำ
- น้ำเสียงเป็นธรรมชาติ เป็นมิตร และเน้นช่วยปิดการขาย
- ไม่ต้องใส่อีโมจิและสัญลักษณ์พิเศษใดๆ"""

def ask_gemini(message: str, shop_id: str= None, user_id: str = None, session_id: str = None):
    
    # 2. ใช้ propagate_attributes ครอบบล็อกการทำงานหลักเอาไว้
    with propagate_attributes(user_id=user_id, session_id=session_id):
        
        # 3. ลบ user_id และ session_id ออกจากพารามิเตอร์ด้านล่างนี้
        with langfuse.start_as_current_observation(
            as_type="generation",
            name="gemini-response",
            model="gemini-2.5-flash-lite",
            metadata={
                "shop_id": shop_id
            },
        ) as generation:
            
            response = client.models.generate_content(
                model="gemini-2.5-flash-lite",
                contents=message,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt
                )
            )
            usage = response.usage_metadata
            
            generation.update(
                input=message,
                output=response.text,
                usage_details={
                    "input": usage.prompt_token_count,
                    "output": usage.candidates_token_count,
                    "total": usage.total_token_count,
                },
                metadata={
                    "shop_id": shop_id
                },
            )

    langfuse.flush()
    print("LANGFUSE FLUSHED")
    
    return {
        "text": response.text,
        "usage": usage
    }