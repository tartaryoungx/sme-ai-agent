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

    cache_result = get_or_create_cache(shop_id or "default")
    cache_name = cache_result["cache_name"]
    cached = cache_result["cached"]
    knowledge_base = cache_result.get("knowledge_base", "")

    # build system prompt ตาม cache status
    full_system_prompt = system_prompt
    if not cached and knowledge_base:
        # fallback: inject knowledge base เข้า prompt ตรงๆ
        full_system_prompt += f"\n\nข้อมูลของร้าน:\n{knowledge_base}"

    prompt = ChatPromptTemplate.from_messages([
        ("system", full_system_prompt),
        MessagesPlaceholder(variable_name="history"),
        ("human", "{input}"),
    ])

    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash-lite",
        google_api_key=settings.GEMINI_API_KEY,
        temperature=0.7,
        **({"cached_content": cache_name} if cache_name else {}),
    )

    chain = prompt | llm

    with propagate_attributes(user_id=user_id, session_id=sid):
        with langfuse.start_as_current_observation(
            as_type="generation",
            name="langchain-agent-response",
            model="gemini-2.5-flash-lite",
            metadata={
                "shop_id": shop_id,
                "cache_used": cached,                              # ← log บอกว่าใช้ cache ไหม
                "cache_reason": cache_result.get("reason", None), # ← log บอกเหตุผลถ้าไม่ได้ใช้
            },
        ) as generation:

            result = chain.invoke({
                "input": message,
                "history": history,
            })
            reply = result.content

            # ดึง token usage จาก LangChain response_metadata
            usage_meta = result.response_metadata.get("usage_metadata", {})
            input_tokens  = usage_meta.get("prompt_token_count", 0)
            output_tokens = usage_meta.get("candidates_token_count", 0)
            cached_tokens = usage_meta.get("cached_content_token_count", 0)

            # Gemini 2.5 Flash Lite pricing (USD per 1M tokens)
            # https://ai.google.dev/pricing
            non_cached_tokens = input_tokens - cached_tokens
            input_cost  = (non_cached_tokens * 0.10 + cached_tokens * 0.025) / 1_000_000
            output_cost = output_tokens * 0.40 / 1_000_000

            generation.update(
                input=message,
                output=reply,
                usage_details={
                    "input":  input_tokens,
                    "output": output_tokens,
                    "total":  input_tokens + output_tokens,
                },
                cost_details={
                    "input":  input_cost,
                    "output": output_cost,
                    "total":  input_cost + output_cost,
                },
                metadata={
                    "shop_id":       shop_id,
                    "cache_used":    cached,
                    "cached_tokens": cached_tokens,
                },
            )

            langfuse.flush()
    save_history(sid, message, reply)

    return {
        "text": reply,
        "session_id": sid,
        "cache_used": cached,  # ← ส่งกลับให้ caller รู้ด้วย
    }