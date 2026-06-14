import re
import uuid
from typing import Optional

from google import genai
from google.genai import types

from app.database import supabase
from app.config import settings
from app.services.token_usage import log_token_usage


client = genai.Client(api_key=settings.GEMINI_API_KEY)
EMBED_MODEL = "gemini-embedding-001"


IMPORTANT_HEADINGS = [
    "ราคา",
    "ค่าติดตั้ง",
    "ค่าบริการ",
    "การจัดส่ง",
    "รับประกัน",
    "สินค้า",
    "รุ่น",
    "FAQ",
    "คำถามที่พบบ่อย",
    "เงื่อนไข",
    "โปรโมชัน",
]


def detect_heading(line: str) -> Optional[str]:
    clean = line.strip()

    if not clean:
        return None

    if clean.startswith("#"):
        return clean.replace("#", "").strip()

    if re.match(r"^\d+[\.\)]\s+", clean):
        return re.sub(r"^\d+[\.\)]\s+", "", clean).strip()

    for heading in IMPORTANT_HEADINGS:
        if heading in clean and len(clean) <= 80:
            return clean

    return None


def split_blocks(text: str):
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # แยกตามย่อหน้าก่อน
    paragraphs = re.split(r"\n\s*\n", text)

    blocks = []

    for paragraph in paragraphs:
        paragraph = paragraph.strip()
        if not paragraph:
            continue

        # ถ้าย่อหน้ายาวมาก ค่อยแยกตามบรรทัด
        if len(paragraph) > 1600:
            lines = [line.strip() for line in paragraph.split("\n") if line.strip()]
            blocks.extend(lines)
        else:
            blocks.append(paragraph)

    return blocks


def chunk_text(text: str, chunk_size: int = 800, overlap: int = 120):
    blocks = split_blocks(text)

    chunks = []
    current = ""
    current_heading = None

    def add_chunk(content: str, heading: Optional[str]):
        content = content.strip()
        if not content:
            return

        # ใส่ heading ซ้ำใน content เพื่อช่วย semantic search
        if heading:
            content = f"หัวข้อ: {heading}\n{content}"

        chunks.append({
            "content": content,
            "heading": heading,
        })

    for block in blocks:
        heading = detect_heading(block)

        if heading:
            add_chunk(current, current_heading)
            current = ""
            current_heading = heading

        # ถ้า block เดี่ยวยาวเกิน chunk_size ให้แตกด้วย overlap
        if len(block) > chunk_size:
            add_chunk(current, current_heading)
            current = ""

            start = 0
            while start < len(block):
                end = start + chunk_size
                piece = block[start:end].strip()

                if piece:
                    add_chunk(piece, current_heading)

                start += chunk_size - overlap

            continue

        # ถ้ารวมแล้วเกิน chunk_size ให้ปิด chunk ก่อน
        if len(current) + len(block) + 2 > chunk_size:
            old_tail = current[-overlap:] if current else ""
            add_chunk(current, current_heading)

            current = ""
            if old_tail:
                current = old_tail.strip() + "\n\n"

        current += block + "\n\n"

    add_chunk(current, current_heading)

    return chunks


def embed(text: str, shop_id: str | None = None):
    token_result = client.models.count_tokens(
        model=EMBED_MODEL,
        contents=text,
    )

    response = client.models.embed_content(
        model=EMBED_MODEL,
        contents=text,
        config=types.EmbedContentConfig(
            output_dimensionality=768
        )
    )

    vector = response.embeddings[0].values

    usage = {
        "prompt_token_count": token_result.total_tokens,
        "candidates_token_count": 0,
        "total_token_count": token_result.total_tokens,
    }

    if shop_id:
        log_token_usage(
            shop_id=shop_id,
            model=EMBED_MODEL,
            usage=usage,
        )

    return vector


def add_doc(
    shop_id: str,
    content: str,
    source: str = "raw_text",
    file_type: str = "text",
):
    document_id = str(uuid.uuid4())
    chunks = chunk_text(content)

    rows = []

    for i, chunk in enumerate(chunks):
        chunk_content = chunk["content"]

        rows.append({
            "shop_id": shop_id,
            "content": chunk_content,
            "chunk_index": i,
            "embedding": embed(chunk_content, shop_id=shop_id),
            "document_id": document_id,

            # เพิ่ม metadata
            "source": source,
            "file_type": file_type,
            "heading": chunk.get("heading"),
        })

    if rows:
        supabase.table("documents").insert(rows).execute()

    return {
        "document_id": document_id,
        "chunks_count": len(rows),
    }


def search_docs(shop_id: str, question: str, match_count: int = 3):
    res = supabase.rpc("match_documents", {
        "query_embedding": embed(question, shop_id),
        "match_shop_id": shop_id,
        "match_count": match_count,
    }).execute()

    return res.data


def debug_chunks(content: str, limit: int = 10):
    chunks = chunk_text(content)

    print("TOTAL CHUNKS:", len(chunks))

    for i, chunk in enumerate(chunks[:limit]):
        print("=" * 80)
        print("CHUNK:", i)
        print("HEADING:", chunk.get("heading"))
        print("LENGTH:", len(chunk["content"]))
        print("-" * 80)
        print(chunk["content"][:1000])


