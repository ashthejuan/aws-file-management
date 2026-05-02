import json
from typing import Any


DEFAULT_HEADERS = {
    "Content-Type": "application/json",
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Headers": "Content-Type,Authorization",
    "Access-Control-Allow-Methods": "OPTIONS,POST,GET,DELETE",
}


def json_response(status_code: int, body: Any = None, headers: dict[str, str] | None = None) -> dict[str, Any]:
    response_headers = {**DEFAULT_HEADERS, **(headers or {})}
    if status_code == 204:
        return {"statusCode": status_code, "headers": response_headers, "body": ""}

    return {
        "statusCode": status_code,
        "headers": response_headers,
        "body": json.dumps(body if body is not None else {}),
    }


def error_response(status_code: int, message: str) -> dict[str, Any]:
    return json_response(status_code, {"error": message})
