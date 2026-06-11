from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage
from langfuse import Langfuse, propagate_attributes
from app.config import settings
from app.ai.cache_manager import get_or_create_cache  # ← เพิ่ม

langfuse = Langfuse(
    public_key=settings.LANGFUSE_PUBLIC_KEY,
    secret_key=settings.LANGFUSE_SECRET_KEY,
    base_url=settings.LANGFUSE_BASE_URL,
)

_memory_store: dict[str, list[BaseMessage]] = {}
MAX_HISTORY = 20

def get_history(session_id: str) -> list[BaseMessage]:
    return _memory_store.setdefault(session_id, [])

def save_history(session_id: str, human_msg: str, ai_msg: str) -> None:
    history = get_history(session_id)
    history.append(HumanMessage(content=human_msg))
    history.append(AIMessage(content=ai_msg))
    if len(history) > MAX_HISTORY:
        _memory_store[session_id] = history[-MAX_HISTORY:]

system_prompt = """คุณคือแอดมินขายสินค้า SME
กฎ:
- ตอบเป็นภาษาไทย
- ตอบไม่เกิน 3 ประโยค
- ถ้าถามเรื่องราคา ให้ตอบราคาโดยตรง
- ถ้าข้อมูลไม่พอ ให้ถามกลับ 1 คำถาม
- ห้ามเขียนเกิน 100 คำ
- น้ำเสียงเป็นธรรมชาติ เป็นมิตร และเน้นช่วยปิดการขาย
- ไม่ต้องใส่อีโมจิและสัญลักษณ์พิเศษใดๆ"""

prompt = ChatPromptTemplate.from_messages([
    ("system", system_prompt),
    MessagesPlaceholder(variable_name="history"),
    ("human", "{input}"),
])

def ask_agent(message: str, shop_id: str = None, user_id: str = None, session_id: str = None):

    sid = session_id or user_id or "default"
    history = get_history(sid)

    # ดึง cache_name ของ shop นี้ (สร้างใหม่ถ้ายังไม่มีหรือหมดอายุ)
    # cache_name = get_or_create_cache(shop_id or "default")  # ← เพิ่ม

    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash-lite",
        google_api_key=settings.GEMINI_API_KEY,
        temperature=0.7,
        # cached_content=cache_name,  # ← เพิ่ม: บอก Gemini ให้ใช้ cache นี้
    )

    chain = prompt | llm

    with propagate_attributes(user_id=user_id, session_id=sid):
        with langfuse.start_as_current_observation(
            as_type="generation",
            name="langchain-agent-response",
            model="gemini-2.5-flash-lite",
            metadata={
                "shop_id": shop_id,
                # "cache_name": cache_name,  # ← log ด้วยว่าใช้ cache ไหน
            },
        ) as generation:

            result = chain.invoke({
                "input": message,
                "history": history,
            })
            reply = result.content

            generation.update(
                input=message,
                output=reply,
                metadata={"shop_id": shop_id},
            )

    langfuse.flush()
    save_history(sid, message, reply)

    return {
        "text": reply,
        "session_id": sid,
    }