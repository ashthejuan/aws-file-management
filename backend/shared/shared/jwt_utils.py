import os
import time
from typing import Any

import jwt


JWT_ALGORITHM = "HS256"


def get_jwt_ttl_seconds() -> int:
    return int(os.environ.get("JWT_TTL_SECONDS", "3600"))


def generate_jwt(user_id: str) -> tuple[str, int]:
    ttl = get_jwt_ttl_seconds()
    now = int(time.time())
    payload = {
        "sub": user_id,
        "iat": now,
        "exp": now + ttl,
    }
    token = jwt.encode(payload, os.environ["JWT_SECRET"], algorithm=JWT_ALGORITHM)
    return token, ttl


def decode_jwt(token: str) -> dict[str, Any]:
    return jwt.decode(token, os.environ["JWT_SECRET"], algorithms=[JWT_ALGORITHM])
