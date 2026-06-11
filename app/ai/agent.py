from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.memory import ConversationBufferWindowMemory
from langchain.chains import ConversationChain
from langchain.prompts import PromptTemplate
from langfuse import Langfuse, propagate_attributes
from app.config import settings

langfuse = Langfuse(
    public_key=settings.LANGFUSE_PUBLIC_KEY,
    secret_key=settings.LANGFUSE_SECRET_KEY,
    base_url=settings.LANGFUSE_BASE_URL,
)

# memory store แยกตาม session — { session_id: memory }
_memory_store: dict[str, ConversationBufferWindowMemory] = {}

def get_memory(session_id: str) -> ConversationBufferWindowMemory:
    if session_id not in _memory_store:
        _memory_store[session_id] = ConversationBufferWindowMemory(
            k=10,  # จำแค่ 10 messages ล่าสุด ประหยัด token
            return_messages=True
        )
    return _memory_store[session_id]

system_prompt = """คุณคือแอดมินขายสินค้า SME
กฎ:
- ตอบเป็นภาษาไทย
- ตอบไม่เกิน 3 ประโยค
- ถ้าถามเรื่องราคา ให้ตอบราคาโดยตรง
- ถ้าข้อมูลไม่พอ ให้ถามกลับ 1 คำถาม
- ห้ามเขียนเกิน 100 คำ
- น้ำเสียงเป็นธรรมชาติ เป็นมิตร และเน้นช่วยปิดการขาย
- ไม่ต้องใส่อีโมจิและสัญลักษณ์พิเศษใดๆ

บทสนทนาที่ผ่านมา:
{history}

ลูกค้า: {input}
แอดมิน:"""

prompt = PromptTemplate(
    input_variables=["history", "input"],
    template=system_prompt
)

def ask_agent(message: str, shop_id: str = None, user_id: str = None, session_id: str = None):
    
    # ใช้ session_id แยก memory ต่อ user
    sid = session_id or user_id or "default"
    memory = get_memory(sid)

    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash-lite",
        google_api_key=settings.GEMINI_API_KEY,
        temperature=0.7,
    )

    chain = ConversationChain(
        llm=llm,
        memory=memory,
        prompt=prompt,
        verbose=False
    )

    with propagate_attributes(user_id=user_id, session_id=sid):
        with langfuse.start_as_current_observation(
            as_type="generation",
            name="langchain-agent-response",
            model="gemini-2.5-flash-lite",
            metadata={"shop_id": shop_id},
        ) as generation:

            result = chain.invoke({"input": message})
            reply = result["response"]

            # นับ token คร่าวๆ (LangChain ไม่ return usage เหมือน SDK)
            generation.update(
                input=message,
                output=reply,
                metadata={"shop_id": shop_id},
            )

    langfuse.flush()

    return {
        "text": reply,
        "session_id": sid,
    }