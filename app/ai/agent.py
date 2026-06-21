from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage
from langfuse import Langfuse, propagate_attributes
from app.config import settings
from app.ai.cache_manager import get_or_create_cache
from app.services.token_usage import log_token_usage
from app.ai.semantic_cache import get_cached_answer, store_in_cache
from app.ai.model_router import route_model, MODEL_LITE, MODEL_FLASH
from app.ai.rag import retrieve_rag_context

langfuse = Langfuse(
    public_key=settings.LANGFUSE_PUBLIC_KEY,
    secret_key=settings.LANGFUSE_SECRET_KEY,
    base_url=settings.LANGFUSE_BASE_URL,
)

_memory_store: dict[str, list[BaseMessage]] = {}
MAX_HISTORY = 20


def ask_agent(user_input: str, shop_id: str = None, user_id: str = None, session_id: str = None):

    sid = session_id or user_id or "default"
    history = get_history(sid) #history prompt


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
    cache_name = cache_result["cache_name"] #refference cache
    cached = cache_result["cached"] #yes or no
    #knowledge_base = cache_result.get("knowledge_base", "")
    RAG_doc_prompt = ""
    #tartar =========================================================
    rag_context = retrieve_rag_context(user_input, shop_id)
    if rag_context:
        RAG_doc_prompt += f"""

    ข้อมูลอ้างอิงจากร้าน:
    {rag_context}

    กฎการใช้ข้อมูล:
    - ใช้ข้อมูลอ้างอิงนี้ตอบลูกค้าเป็นหลัก
    - ถ้าข้อมูลไม่พอ ให้ถามกลับ 1 คำถาม
    - ห้ามแต่งข้อมูลเอง
    """
    #tartar =========================================================

    #if not cached and knowledge_base:
        # fallback: inject knowledge base เข้า prompt ตรงๆ
    #    full_system_prompt += f"\n\nข้อมูลของร้าน:\n{knowledge_base}"

    prompt = ChatPromptTemplate.from_messages([
        MessagesPlaceholder(variable_name="history"),
        ("human", """
        User question:
        {input}

        Relevant documents:
        {rag}
        """),
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

    result = langfuse_with_invoke(
    prompt=prompt,
    chain=chain,
    user_input=user_input,
    history=history,
    rag_prompt=RAG_doc_prompt,
    user_id=user_id,
    session_id=session_id,
    shop_id=shop_id,
    cached=cached,
    cache_name=cache_name,
    cache_result=cache_result,
    )
    reply = result.content
    save_history(sid, user_input, reply)

    return {
        "text": reply,
        "session_id": sid,
        "cache_used": cached,
        "rag_used": bool(rag_context),
    }

def get_history(session_id: str) -> list[BaseMessage]:
    return _memory_store.setdefault(session_id, [])



def save_history(session_id: str, human_msg: str, ai_msg: str) -> None:
    history = get_history(session_id)
    history.append(HumanMessage(content=human_msg))
    history.append(AIMessage(content=ai_msg))
    if len(history) > MAX_HISTORY:
        _memory_store[session_id] = history[-MAX_HISTORY:]

def langfuse_with_invoke(
    prompt,
    chain,
    user_input: str,
    history,
    rag_prompt: str,
    user_id: str,
    session_id: str,
    shop_id: str,
    cached: bool,
    cache_name: str | None,
    cache_result: dict,
):
    sid = session_id or user_id or "default"
    invoke_input = {
        "input": user_input,
        "history": history,
        "rag": rag_prompt,
    }    
 # print prompt ที่ LangChain สร้างจริง ######TEST####
    """
    prompt_value = prompt.invoke(invoke_input)

    print("\n===== CACHE =====")
    print(f"cache_used: {cached}")
    print(f"cache_name: {cache_name}")
    print(f"cache_reason: {cache_result.get('reason')}")

    print("\n===== PROMPT SENT TO LLM (not include cached content text) =====")
    for msg in prompt_value.to_messages():
        print(f"\n[{msg.type}]")
        print(msg.content)    
    """
    print(f"[SID] {sid}")
    print(history)
    with propagate_attributes(user_id=user_id, session_id=sid):
        with langfuse.start_as_current_observation(
            as_type="generation",
            name="langchain-agent-response",
            model=selected_model,
            metadata={
                "shop_id": shop_id,
                "cache_used": cached,
                "cache_reason": cache_result.get("reason"),
            },
        ) as generation:

            result = chain.invoke(invoke_input)

            reply = result.content

            usage = result.usage_metadata or {}
            input_tokens = usage.get("input_tokens", 0)
            output_tokens = usage.get("output_tokens", 0)
            cached_tokens = (
                usage.get("input_token_details") or {}
            ).get("cache_read", 0)

            generation.update(
                input=user_input,
                output=reply,
                usage_details={
                    "input": input_tokens,
                    "output": output_tokens,
                    "total": input_tokens + output_tokens,
                },
                metadata={
                    "shop_id": shop_id,
                    "cache_used": cached,
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

            return result
