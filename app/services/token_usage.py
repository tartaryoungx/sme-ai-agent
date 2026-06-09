from app.database import supabase
def log_token_usage(shop_id: str, session_id: str | None, model: str, usage):
            try:
                supabase.table("token_usage").insert({
                    "shop_id": shop_id,
                    "session_id": session_id,
                    "model": model,
                    "input_tokens": usage.prompt_token_count or 0,
                    "output_tokens": usage.candidates_token_count or 0,
                    "cached_tokens": usage.cached_content_token_count or 0,
                    "cost_usd": 0,
                    "cache_hit": bool(usage.cached_content_token_count),
                }).execute()
                
            except Exception as e:
                print("TOKEN LOG INSERT FAILED:", e)