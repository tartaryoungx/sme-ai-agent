def normalize_usage(usage) -> dict:
    if usage is None:
        return {
            "input_tokens": 0,
            "output_tokens": 0,
            "total_tokens": 0,
            "cached_tokens": 0,
        }

    if isinstance(usage, dict):
        input_tokens = (
            usage.get("input_tokens")
            or usage.get("prompt_token_count")
            or 0
        )
        output_tokens = (
            usage.get("output_tokens")
            or usage.get("candidates_token_count")
            or 0
        )
        total_tokens = (
            usage.get("total_tokens")
            or usage.get("total_token_count")
            or input_tokens + output_tokens
        )
        cached_tokens = (
            usage.get("cached_tokens")
            or usage.get("cached_content_token_count")
            or 0
        )
        return {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": total_tokens,
            "cached_tokens": cached_tokens,
        }

    input_tokens = getattr(usage, "prompt_token_count", 0)
    output_tokens = getattr(usage, "candidates_token_count", 0)
    total_tokens = getattr(usage, "total_token_count", input_tokens + output_tokens)
    cached_tokens = getattr(usage, "cached_content_token_count", 0) or 0

    return {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": total_tokens,
        "cached_tokens": cached_tokens,
    }