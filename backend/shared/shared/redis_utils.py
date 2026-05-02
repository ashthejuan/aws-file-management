import os

import redis


redis_client: redis.Redis | None = None


def get_redis_client() -> redis.Redis:
    global redis_client
    if redis_client is None:
        redis_client = redis.Redis(
            host=os.environ.get("REDIS_ENDPOINT", "localhost"),
            port=int(os.environ.get("REDIS_PORT", "6379")),
            decode_responses=True,
            socket_connect_timeout=3,
            socket_timeout=3,
        )
    return redis_client


def cache_jwt(token: str, user_id: str, ttl_seconds: int) -> None:
    get_redis_client().setex(token, ttl_seconds, user_id)


def get_cached_user_id(token: str) -> str | None:
    return get_redis_client().get(token)


def invalidate_jwt(token: str) -> None:
    get_redis_client().delete(token)
