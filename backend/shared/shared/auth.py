import jwt

from .jwt_utils import decode_jwt
from .redis_utils import get_cached_user_id


class Unauthorized(Exception):
    """Raised when a request does not include a valid cached bearer token."""


def get_bearer_token(event: dict) -> str:
    headers = {key.lower(): value for key, value in (event.get("headers") or {}).items()}
    auth_header = headers.get("authorization", "")
    prefix = "Bearer "
    if not auth_header.startswith(prefix):
        raise Unauthorized("Missing bearer token")
    return auth_header[len(prefix) :].strip()


def require_auth(event: dict) -> str:
    token = get_bearer_token(event)
    try:
        payload = decode_jwt(token)
    except jwt.ExpiredSignatureError as exc:
        raise Unauthorized("Token expired") from exc
    except jwt.InvalidTokenError as exc:
        raise Unauthorized("Invalid token") from exc

    user_id = payload.get("sub")
    if not user_id:
        raise Unauthorized("Invalid token subject")

    cached_user_id = get_cached_user_id(token)
    if cached_user_id != user_id:
        raise Unauthorized("Token is no longer active")

    return user_id
