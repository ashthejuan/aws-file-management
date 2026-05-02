import json
import logging
import time
import uuid
from typing import Any

from boto3.dynamodb.conditions import Key

from shared.dynamodb_utils import get_users_table
from shared.jwt_utils import generate_jwt
from shared.password import hash_password, verify_password
from shared.redis_utils import cache_jwt
from shared.responses import error_response, json_response


EMAIL_INDEX_NAME = "EmailIndex"
logger = logging.getLogger(__name__)


def _parse_json_body(event: dict[str, Any]) -> dict[str, Any]:
    try:
        body = json.loads(event.get("body") or "{}")
    except json.JSONDecodeError as exc:
        raise ValueError("Request body must be valid JSON") from exc
    if not isinstance(body, dict):
        raise ValueError("Request body must be a JSON object")
    return body


def _normalize_email(value: str) -> str:
    return value.strip().lower()


def _find_user_by_email(email: str) -> dict[str, Any] | None:
    users_table = get_users_table()
    response = users_table.query(
        IndexName=EMAIL_INDEX_NAME,
        KeyConditionExpression=Key("email").eq(email),
        Limit=1,
    )
    items = response.get("Items", [])
    return items[0] if items else None


def _issue_token(user_id: str) -> dict[str, Any]:
    token, ttl = generate_jwt(user_id)
    cache_jwt(token, user_id, ttl)
    return {"token": token, "expiresIn": ttl}


def signup_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    try:
        body = _parse_json_body(event)
        email = _normalize_email(str(body.get("email", "")))
        password = str(body.get("password", ""))

        if not email or not password:
            return error_response(400, "email and password are required")
        if len(password) < 8:
            return error_response(400, "password must be at least 8 characters")
        if _find_user_by_email(email) is not None:
            return error_response(409, "email is already registered")

        user_id = str(uuid.uuid4())
        get_users_table().put_item(
            Item={
                "userId": user_id,
                "email": email,
                "passwordHash": hash_password(password),
                "createdAt": int(time.time()),
            },
            ConditionExpression="attribute_not_exists(userId)",
        )

        return json_response(201, _issue_token(user_id))
    except ValueError as exc:
        return error_response(400, str(exc))
    except Exception:
        logger.exception("Signup failed")
        return error_response(500, "Internal server error")


def login_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    try:
        body = _parse_json_body(event)
        email = _normalize_email(str(body.get("email", "")))
        password = str(body.get("password", ""))

        if not email or not password:
            return error_response(400, "email and password are required")

        user = _find_user_by_email(email)
        if user is None or not verify_password(password, user.get("passwordHash", "")):
            return error_response(401, "Invalid credentials")

        return json_response(200, _issue_token(user["userId"]))
    except ValueError as exc:
        return error_response(400, str(exc))
    except Exception:
        logger.exception("Login failed")
        return error_response(500, "Internal server error")
