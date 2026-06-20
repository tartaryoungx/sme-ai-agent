from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage
from langfuse import Langfuse, propagate_attributes
from app.config import settings
from app.ai.cache_manager import get_or_create_cache
from app.services.token_usage import log_token_usage
from app.ai.semantic_cache import get_cached_answer, store_in_cache
from app.ai.model_router import route_model, MODEL_LITE, MODEL_FLASH
from app.ai.rag import retrieve_top_k

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


def ask_agent(message: str, shop_id: str = None, user_id: str = None, session_id: str = None):

    sid = session_id or user_id or "default"
    history = get_history(sid)


    try:
        semantic_answer = get_cached_answer(shop_id or "default", message)
        if semantic_answer:
            print(f"[SEMANTIC CACHE HIT] shop={shop_id} → return cached answer")
            save_history(sid, message, semantic_answer)
            return {
                "text": semantic_answer,
                "session_id": sid,
                "cache_used": False,
                "semantic_cache_hit": True,
            }
    except Exception as e:
        print(f"[SEMANTIC CACHE ERROR] {e}")

    cache_result = get_or_create_cache(shop_id or "default")
    cache_name = cache_result["cache_name"]
    cached = cache_result["cached"]
    knowledge_base = cache_result.get("knowledge_base", "")

    docs = []

    full_system_prompt = system_prompt
    if not cached and knowledge_base:
        full_system_prompt += f"\n\n[ข้อมูลของร้าน — ใช้ข้อมูลนี้ตอบลูกค้า]:\n{knowledge_base}"
    #tartar =========================================================
    rag_chunks = retrieve_top_k(message, shop_id, k=3) if shop_id else []

    rag_context = "\n\n".join(
        f"[ข้อมูล {i+1}]\n{chunk.get('content', '')}"
        for i, chunk in enumerate(rag_chunks)
        if chunk.get("content")
    )
    top_1_rag_content = rag_chunks[0].get("content") if rag_chunks else None
    #tartar =========================================================

    # build system prompt ตาม cache status
    full_system_prompt = system_prompt

    #tartar =========================================================
    if rag_context:
        full_system_prompt += f"""

    ข้อมูลอ้างอิงจากร้าน:
    {rag_context}

    กฎการใช้ข้อมูล:
    - ใช้ข้อมูลอ้างอิงนี้ตอบลูกค้าเป็นหลัก
    - ถ้าข้อมูลไม่พอ ให้ถามกลับ 1 คำถาม
    - ห้ามแต่งข้อมูลเอง
    """
    #tartar =========================================================

    if not cached and knowledge_base:
        # fallback: inject knowledge base เข้า prompt ตรงๆ
        full_system_prompt += f"\n\nข้อมูลของร้าน:\n{knowledge_base}"

    prompt = ChatPromptTemplate.from_messages([
        ("system", full_system_prompt),
        MessagesPlaceholder(variable_name="history"),
        ("human", "{input}"),
    ])

    # ═══════════════════════════════════════════════════════
    # Model Router — เลือกโมเดลตามความซับซ้อนของคำถาม
    # Flash-Lite ($0.10/MTok) สำหรับคำถามง่าย
    # Flash      ($0.30/MTok) สำหรับคำถามซับซ้อน
    # ═══════════════════════════════════════════════════════
    selected_model = route_model(message)

    # Context cache ใช้ได้เฉพาะ Flash-Lite เท่านั้น
    cache_kwargs = (
        {"cached_content": cache_name}
        if cache_name and selected_model == MODEL_LITE
        else {}
    )

    llm = ChatGoogleGenerativeAI(
        model=selected_model,
        google_api_key=settings.GEMINI_API_KEY,
        temperature=0.7,
        **cache_kwargs,
    )

    chain = prompt | llm

    with propagate_attributes(user_id=user_id, session_id=sid):
        with langfuse.start_as_current_observation(
            as_type="generation",
            name="langchain-agent-response",
            model=selected_model,
            metadata={
                "shop_id": shop_id,
                "model_selected": selected_model,
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
                model=selected_model,
                usage={
                    "input_tokens":  input_tokens,
                    "output_tokens": output_tokens,
                    "total_tokens":  input_tokens + output_tokens,
                    "cached_tokens": cached_tokens,
                },
            )

            langfuse.flush()
    save_history(sid, message, reply)


    try:
        store_in_cache(shop_id or "default", message, reply)
    except Exception as e:
        print(f"[SEMANTIC CACHE STORE ERROR] {e}")

    return {
        "text": reply,
        "session_id": sid,
        "cache_used": cached,
        "semantic_cache_hit": False,
        "model_used": selected_model,
        "rag_used": bool(rag_context),
        "rag_chunks_count": len(rag_chunks),
        "top_1_rag": top_1_rag_content,
    }