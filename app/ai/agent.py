from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage
from langfuse import Langfuse, propagate_attributes
from app.config import settings

langfuse = Langfuse(
    public_key=settings.LANGFUSE_PUBLIC_KEY,
    secret_key=settings.LANGFUSE_SECRET_KEY,
    base_url=settings.LANGFUSE_BASE_URL,
)

# memory store แยกตาม session — { session_id: list[BaseMessage] }
_memory_store: dict[str, list[BaseMessage]] = {}

MAX_HISTORY = 20  # 10 turns = 20 messages (human + ai)

def get_history(session_id: str) -> list[BaseMessage]:
    return _memory_store.setdefault(session_id, [])

def save_history(session_id: str, human_msg: str, ai_msg: str) -> None:
    history = get_history(session_id)
    history.append(HumanMessage(content=human_msg))
    history.append(AIMessage(content=ai_msg))
    # จำแค่ MAX_HISTORY messages ล่าสุด ประหยัด token
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

    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash-lite",
        google_api_key=settings.GEMINI_API_KEY,
        temperature=0.7,
    )

    # LCEL chain บริสุทธิ์ ไม่มี deprecated wrapper
    chain = prompt | llm

    with propagate_attributes(user_id=user_id, session_id=sid):
        with langfuse.start_as_current_observation(
            as_type="generation",
            name="langchain-agent-response",
            model="gemini-2.5-flash-lite",
            metadata={"shop_id": shop_id},
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

    # บันทึก history หลัง invoke
    save_history(sid, message, reply)

    return {
        "text": reply,
        "session_id": sid,
    }