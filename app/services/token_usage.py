from app.database import supabase
from app.services.norm import normalize_usage
def log_token_usage(shop_id: str, model: str, usage, session_id: str | None = None, latency_ms: int | None = None,):
            
            usage_data = normalize_usage(usage)

            #print(usage_data)
            try:
                supabase.table("token_usage").insert({
                    "shop_id": shop_id,
                    "session_id": session_id,
                    "model": model,
                    "input_tokens": usage_data["input_tokens"],
                    "output_tokens": usage_data["output_tokens"],
                    "cached_tokens": usage_data["cached_tokens"],
                    "cache_hit": usage_data["cached_tokens"] > 0,
                    "latency_ms": latency_ms,
                    # "cost_usd": calculate_cost(...)
                }).execute()
#                print(f"Logged token usage for shop_id: {shop_id}, session_id: {session_id}")
                
            except Exception as e:
                print("TOKEN LOG INSERT FAILED:", e)