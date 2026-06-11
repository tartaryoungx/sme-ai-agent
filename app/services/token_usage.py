from app.database import supabase
def log_token_usage(shop_id: str, session_id: str | None, model: str, usage, latency_ms: int,):
            input_tokens = usage.prompt_token_count or 0
            output_tokens = usage.candidates_token_count or 0
            cached_tokens = getattr(usage, "cached_content_token_count", 0) or 0
            try:
                supabase.table("token_usage").insert({
                    "shop_id": shop_id,
                    "session_id": session_id,
                    "model": model,
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "cached_tokens": cached_tokens,
                    "cache_hit": cached_tokens > 0,
                    "latency_ms": latency_ms,
                    # "cost_usd": calculate_cost(...)
                }).execute()
                print(f"Logged token usage for shop_id: {shop_id}, session_id: {session_id}")
                
            except Exception as e:
                print("TOKEN LOG INSERT FAILED:", e)