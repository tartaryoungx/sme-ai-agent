from app.database import supabase
from app.ai.rag import embed   
import time


SIMILARITY_THRESHOLD = 0.92

def get_cached_answer(shop_id: str, question: str) -> str | None:

    query_vector = embed(question, shop_id=shop_id)

    result = supabase.rpc("match_semantic_cache", {
        "query_embedding": query_vector,
        "match_shop_id": shop_id,
        "similarity_threshold": SIMILARITY_THRESHOLD,
        "match_count": 1,
    }).execute()

    if not result.data:
        return None   # cache miss

    best_match = result.data[0]
    cached_id = best_match["id"]
    similarity = best_match["similarity"]

    print(f"[SEMANTIC CACHE HIT] shop={shop_id} similarity={similarity:.3f}")

    #ครอบ try/except แยก เพื่อไม่ให้ block การ return คำตอบ
    try:
        supabase.rpc("increment_semantic_cache_hit", {"cache_id": cached_id}).execute()
    except Exception as stat_err:
        print(f"[SEMANTIC CACHE STAT ERROR] {stat_err}")

    return best_match["answer"]  


def store_in_cache(shop_id: str, question: str, answer: str) -> None:

    question_vector = embed(question, shop_id=shop_id)

    existing = supabase.rpc("match_semantic_cache", {
        "query_embedding": question_vector,
        "match_shop_id": shop_id,
        "similarity_threshold": SIMILARITY_THRESHOLD,
        "match_count": 1,
    }).execute()

    if existing.data:
        print(f"[SEMANTIC CACHE SKIP] already exists similarity={existing.data[0]['similarity']:.3f}")
        return 

    supabase.table("semantic_cache").insert({
        "shop_id": shop_id,
        "question": question,
        "answer": answer,
        "embedding": question_vector,
    }).execute()

    print(f"[SEMANTIC CACHE STORED] shop={shop_id} q={question[:50]}")
