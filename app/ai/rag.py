from app.database  import supabase
from google import genai
from google.genai import types
from app.config import settings
from app.services.token_usage import log_token_usage

client = genai.Client(api_key=settings.GEMINI_API_KEY)
EMBED_MODEL = "gemini-embedding-001"

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

def add_doc(shop_id: str, content: str):
    supabase.table("documents").insert({
        "shop_id": shop_id,
        "content": content,
        "embedding": embed(content, shop_id=shop_id)
    }).execute()

def search_docs(shop_id: str, question: str, match_count: int = 3, match_threshold: float = 0.5):
    embedding = embed(question, shop_id=shop_id)
    print(f"[RAG SEARCH] shop={shop_id} threshold={match_threshold} count={match_count}")

    res = supabase.rpc("match_documents", {
        "query_embedding": embedding,
        "match_shop_id": shop_id,
        "match_count": match_count,
        "match_threshold": match_threshold,
    }).execute()

    results = res.data or []
    print(f"[RAG SEARCH] returned {len(results)} docs: {[d.get('content', '')[:60] for d in results]}")
    return results

