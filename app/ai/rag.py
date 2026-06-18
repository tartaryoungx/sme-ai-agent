from typing import Any

from google import genai
from google.genai import types 
import pymupdf4llm
from langchain_text_splitters import RecursiveCharacterTextSplitter
from app.services.token_usage import log_token_usage
from app.config import settings
from app.database import supabase

EMBED_MODEL = "gemini-embedding-001"
client = genai.Client(api_key=settings.GEMINI_API_KEY)

#กันลืม: 1. semantic Cache  ไม่มี cache -> ยิง LLM ตอบ -> เก็บคำถาม + คำตอบ + embedding ลง cache อัตโนมัติ + shop_id + product_code \
# -> ครั้งต่อไปมีคนถามคล้าย ๆ กัน (95%) -> ดึงคำตอบเก่ามาใช้ แบบที่ 2 คุมคุณภาพเอง ใส่ FAQ เองเลย
# 2. Prompt Cache ไม่ได้ cache คำตอบ แต่ cache บริบทที่ต้องส่งให้ LLM ซ้ำ ๆ (system prompt, กฎการตอบเยอะ,shop profile หลายบรรทัด,brand tone,tool instructions,policy หลัก,summary ร้าน,product category overview)
# 3. Context Compression: summary history
#Rag กุเอง : product spec ละเอียด, ราคาแต่ละรุ่น, คู่มือ/เอกสาร,FAQ รายข้อ,case/review, pdf เยอะๆ

# ======================================================
# Main Flow: PDF -> save Docs -> Chunks -> embeddings + save chunk
# ======================================================

def save_pdf_to_rag(
    pdf_file_path: str,
    shop_id: str | None, 
    title: str | None,
    filename: str,
) -> dict[str, Any]:

    document_id = create_document(
        shop_id=shop_id,
        title=title,
        filename=filename,
    )
    try:
        chunks = create_chunks(
            pdf_path=pdf_file_path,
        )

        save_chunks_to_db(
            document_id=document_id,
            chunks=chunks,
            shop_id=shop_id,
        )
        mark_document_ready(document_id)

        return {
            "document_id": document_id,
            "chunks_count": len(chunks),
            "status": "ready",
        }

    except Exception:
        mark_document_failed_safe(document_id)
        raise

# ======================================================
# DB: Add Documents in DB
# ======================================================

def create_document(
    filename: str,
    shop_id: str | None = None,
    title: str | None = None,
) -> str:

    data = {
        "shop_id": shop_id,
        "file_name": filename,
        "title": title,
        "status": "processing",
    }

    response = (
        supabase
        .table("documents")
        .insert(data)
        .execute()
    )

    if not response.data:
        raise RuntimeError("create_document failed")

    return response.data[0]["id"]

# ======================================================
# Document Status
# ======================================================

def mark_document_ready(document_id: str) -> None:
    response = (
        supabase
        .table("documents")
        .update({
            "status": "ready",
        })
        .eq("id", document_id)
        .execute()
    )

    if not response.data:
        raise RuntimeError("mark_document_ready failed")


def mark_document_failed(document_id: str) -> None:
    (
        supabase
        .table("documents")
        .update({
            "status": "failed",
        })
        .eq("id", document_id)
        .execute()
    )

def mark_document_failed_safe(document_id: str) -> None:
    try:
        mark_document_failed(document_id)
    except Exception:
        pass

def delete_document(document_id: str) -> None:

    (
        supabase
        .table("documents")
        .delete()
        .eq("id", document_id)
        .execute()
    )

# ==================================================================
# Chunk: PDF -> Chunks by "RecursiveCharacter Method"
# ==================================================================

def create_chunks(pdf_path, preview_count=5):
    md_text = pymupdf4llm.to_markdown(pdf_path)

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1800,      # ประมาณ 400 tokens แบบหยาบ ๆ
        chunk_overlap=270,    # ประมาณ 15%
        separators=["\n\n", "\n", " ", ""]
    )

    chunks = splitter.split_text(md_text)

#    print("Total chunks:", len(chunks))

#    for i, chunk in enumerate(chunks[:preview_count]):
#
#        print("=" * 80)
#        print(f"CHUNK {i+1}")
#        print(chunk)

    return chunks


# ==================================================================
# Embed & DB: Embed chunks and save in DB
# ==================================================================

def save_chunks_to_db(
    document_id: str,
    chunks: list[str],
    shop_id: str | None,
):
    for i, chunk in enumerate(chunks):
        vector = embed(
        text=chunk,
        shop_id=shop_id,
        )

        data = {
            "document_id": document_id,
            "shop_id": shop_id,
            "chunk_index": i,
            "content": chunk,
            "embedding_text": None,
            "heading": None,
            "page_start": None,
            "metadata": {},
            "embedding": vector,
        }
            
        response = (
            supabase
            .table("chunks")
            .insert(data)
            .execute()
        )

        if not response.data:
            raise RuntimeError(f"save chunk failed at index {i}")


#embed_chunks + token log
def embed(text: str, shop_id: str | None = None):
    response = client.models.embed_content(
        model=EMBED_MODEL,
        contents=text,
        config=types.EmbedContentConfig(
            output_dimensionality=768
        )
    )

    vector = response.embeddings[0].values

    if shop_id:
        token_result = client.models.count_tokens(
            model=EMBED_MODEL,
            contents=text,
        )

        usage = {
            "prompt_token_count": token_result.total_tokens,
            "candidates_token_count": 0,
            "total_token_count": token_result.total_tokens,
        }

        log_token_usage(
            shop_id=shop_id,
            model=EMBED_MODEL,
            usage=usage,
        )

    return vector

# ==================================================================
# Rag retrieve
# ==================================================================

def embed_query(text: str) -> list[float]:
    res = client.models.embed_content(
        model=EMBED_MODEL,
        contents=text,
        config=types.EmbedContentConfig(output_dimensionality=768)
    )
    return res.embeddings[0].values

def retrieve_top_k(query: str, shop_id: str | None, k: int = 3) -> list[dict]:
    query_vector = embed_query(query)

    res = supabase.rpc(
        "match_document_chunks",
        {
            "query_embedding": query_vector,
            "match_shop_id": shop_id,
            "match_count": k,
        }
    ).execute()

    return res.data or []