import time
from starlette.middleware.base import BaseHTTPMiddleware
from app.db import supabase


class TokenLoggerMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        start_time = time.time()

        response = await call_next(request)

        latency_ms = int((time.time() - start_time) * 1000)

        shop_id = request.headers.get("X-Shop-Id")

        if shop_id:
            supabase.table("token_usage").insert({
                "shop_id": shop_id,
                "session_id": request.headers.get("X-Session-Id"),
                "model": "unknown",
                "input_tokens": 0,
                "output_tokens": 0,
                "cached_tokens": 0,
                "cost_usd": 0,
                "cache_hit": False,
            }).execute()

        print(f"Request finished in {latency_ms}ms")

        return response