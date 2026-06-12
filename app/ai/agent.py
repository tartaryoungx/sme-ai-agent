from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage
from langfuse import Langfuse, propagate_attributes
from app.config import settings
from app.ai.cache_manager import get_or_create_cache
from app.ai.rag import search_docs
from app.services.token_usage import log_token_usage

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

    # --- RAG: ค้นหา document ที่เกี่ยวข้องกับคำถาม ---
    rag_context = ""
    docs = []  # init ก่อน เพื่อป้องกัน scope bug
    try:
        docs = search_docs(shop_id or "default", message, match_count=3)
        print(f"[RAG] shop={shop_id} query='{message[:50]}' found={len(docs)} docs")
        if docs:
            rag_context = "\n".join(
                f"- {d['content']}" for d in docs if d.get("content")
            )
            print(f"[RAG CONTEXT]\n{rag_context[:300]}")
        else:
            print(f"[RAG] No matching documents found for shop={shop_id}")
    except Exception as e:
        import traceback
        print(f"[RAG ERROR] {e}")
        traceback.print_exc()

    # build system prompt ตาม cache status + RAG context
    full_system_prompt = system_prompt
    if not cached and knowledge_base:
        # fallback: inject knowledge base เข้า prompt ตรงๆ (กรณีข้อมูลน้อยกว่า 2048 tokens)
        full_system_prompt += f"\n\nข้อมูลของร้าน:\n{knowledge_base}"
    if rag_context:
        full_system_prompt += f"\n\nข้อมูลที่เกี่ยวข้องกับคำถามนี้:\n{rag_context}"

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
                "cache_used": cached,
                "cache_reason": cache_result.get("reason", None),
                "rag_docs_count": len(docs),
            },
        ) as generation:

            result = chain.invoke({
                "input": message,
                "history": history,
            })
            reply = result.content

            # ดึง token usage จาก LangChain AIMessage.usage_metadata
            usage_meta    = result.usage_metadata or {}
            input_tokens  = usage_meta.get("input_tokens", 0)
            output_tokens = usage_meta.get("output_tokens", 0)
            cached_tokens = (usage_meta.get("input_token_details") or {}).get("cache_read", 0)

            generation.update(
                input=message,
                output=reply,
                usage_details={
                    "input":  input_tokens,
                    "output": output_tokens,
                    "total":  input_tokens + output_tokens,
                },
                metadata={
                    "shop_id":       shop_id,
                    "cache_used":    cached,
                    "cached_tokens": cached_tokens,
                },
            )

            # log token usage (LLM call) ลง Supabase เพื่อให้ Railway log ตรงกับ Langfuse
            log_token_usage(
                shop_id=shop_id or "default",
                session_id=sid,
                model="gemini-2.5-flash-lite",
                usage={
                    "input_tokens":  input_tokens,
                    "output_tokens": output_tokens,
                    "total_tokens":  input_tokens + output_tokens,
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