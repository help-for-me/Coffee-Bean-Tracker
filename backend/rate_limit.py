import time

from fastapi import HTTPException, Request

# Not a general-purpose rate limiter - just a simple per-client cooldown on
# the handful of endpoints that spend the Anthropic API key's quota, so a
# script (or a bug in a client) hammering them can't run up costs. An
# in-memory dict is enough since this app runs as a single process; no
# need for Redis or similar for a self-hosted single-instance app.
_last_call: dict[str, float] = {}


def enforce_cooldown(request: Request, key: str, seconds: float) -> None:
    client_ip = request.client.host if request.client else "unknown"
    bucket_key = f"{client_ip}:{key}"
    now = time.monotonic()
    last = _last_call.get(bucket_key)
    if last is not None and now - last < seconds:
        retry_after = round(seconds - (now - last))
        raise HTTPException(
            status_code=429, detail=f"Please wait {retry_after}s before trying again."
        )
    _last_call[bucket_key] = now
