MODEL_LITE  = "gemini-2.5-flash-lite"   # $0.10 input / $0.40 output per MTok
MODEL_FLASH = "gemini-2.5-flash"        # $0.30 input / $2.50 output per MTok


COMPLEX_KEYWORDS = [
    "เปรียบเทียบ", "วิเคราะห์", "แนะนำ", "recommend",

    "ข้อดีข้อเสีย", "ต่างกันอย่างไร", "อันไหนดีกว่า",

    "ช่วยเขียน", "draft", "สรุป", "อธิบาย", "บอกเหตุผล",

    "ขั้นตอน", "วิธีทำ", "แผน", "กลยุทธ์",
]

MAX_WORDS_FOR_LITE = 30   # ถ้าถามยาวกว่านี้ → Flash

def route_model(message: str) -> str:


    msg_lower = message.lower().strip()

    word_count = len(message.split())
    if word_count > MAX_WORDS_FOR_LITE:
        print(f"[ROUTER] Flash — long message ({word_count} words)")
        return MODEL_FLASH

    for kw in COMPLEX_KEYWORDS:
        if kw in msg_lower:
            print(f"[ROUTER] Flash — keyword '{kw}'")
            return MODEL_FLASH

    multi_signals = ["และ", " กับ ", "ด้วย", "พร้อมกัน", "ทั้งหมด"]
    signal_count = sum(1 for s in multi_signals if s in msg_lower)
    if signal_count >= 2:
        print(f"[ROUTER] Flash — multi-question signals ({signal_count})")
        return MODEL_FLASH

    print(f"[ROUTER] Flash-Lite — simple query")
    return MODEL_LITE
