from fastapi import HTTPException

from app.core.redis import redis


async def enforce_fixed_window_rate_limit(
    *,
    subject: str,
    action: str,
    limit: int,
    window_seconds: int,
):
    if limit <= 0:
        return

    key = f"rate_limit:{action}:{subject}"
    current_count = await redis.incr(key)

    if current_count == 1:
        await redis.expire(key, window_seconds)

    if current_count > limit:
        ttl = await redis.ttl(key)
        retry_after = max(ttl, 1)
        raise HTTPException(
            status_code=429,
            detail=f"Too many {action} requests. Try again in {retry_after} seconds.",
            headers={"Retry-After": str(retry_after)},
        )
