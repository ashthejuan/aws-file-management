import logging
from decimal import Decimal
from typing import Any

from boto3.dynamodb.conditions import Key

from shared.auth import Unauthorized, require_auth
from shared.dynamodb_utils import get_files_table
from shared.responses import error_response, json_response


logger = logging.getLogger(__name__)


def _to_int(value: Any) -> int:
    if isinstance(value, Decimal):
        return int(value)
    return int(value or 0)


def _serialize_file(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "fileId": item["fileId"],
        "fileName": item["fileName"],
        "size": _to_int(item.get("size")),
        "contentType": item.get("contentType", "application/octet-stream"),
        "status": item.get("status", "pending"),
        "uploadedAt": _to_int(item.get("uploadedAt")),
    }


def list_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    try:
        user_id = require_auth(event)
        response = get_files_table().query(KeyConditionExpression=Key("userId").eq(user_id))
        files = [_serialize_file(item) for item in response.get("Items", [])]
        files.sort(key=lambda item: item["uploadedAt"], reverse=True)
        return json_response(200, files)
    except Unauthorized as exc:
        return error_response(401, str(exc))
    except Exception:
        logger.exception("List files failed")
        return error_response(500, "Internal server error")
