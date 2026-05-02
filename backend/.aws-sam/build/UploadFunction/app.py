import json
import logging
import os
import time
import uuid
from pathlib import PurePath
from typing import Any

import boto3

from shared.auth import Unauthorized, require_auth
from shared.dynamodb_utils import get_files_table
from shared.responses import error_response, json_response


DEFAULT_CONTENT_TYPE = "application/octet-stream"
DEFAULT_MAX_UPLOAD_BYTES = 50 * 1024 * 1024
DEFAULT_UPLOAD_URL_TTL_SECONDS = 300
logger = logging.getLogger(__name__)


def _parse_json_body(event: dict[str, Any]) -> dict[str, Any]:
    try:
        body = json.loads(event.get("body") or "{}")
    except json.JSONDecodeError as exc:
        raise ValueError("Request body must be valid JSON") from exc
    if not isinstance(body, dict):
        raise ValueError("Request body must be a JSON object")
    return body


def _clean_file_name(file_name: str) -> str:
    stripped = file_name.strip()
    if not stripped:
        raise ValueError("fileName is required")
    # Avoid allowing clients to choose folder paths inside the bucket.
    if PurePath(stripped).name != stripped or "/" in stripped or "\\" in stripped:
        raise ValueError("fileName must not contain path separators")
    return stripped


def _parse_size(value: Any) -> int:
    try:
        size = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("size must be a positive integer") from exc
    max_size = int(os.environ.get("MAX_UPLOAD_BYTES", str(DEFAULT_MAX_UPLOAD_BYTES)))
    if size <= 0:
        raise ValueError("size must be a positive integer")
    if size > max_size:
        raise ValueError(f"size must be less than or equal to {max_size} bytes")
    return size


def _get_s3_client():
    return boto3.client("s3")


def request_upload_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    try:
        user_id = require_auth(event)
        body = _parse_json_body(event)
        file_name = _clean_file_name(str(body.get("fileName", "")))
        size = _parse_size(body.get("size"))
        content_type = str(body.get("contentType") or DEFAULT_CONTENT_TYPE).strip() or DEFAULT_CONTENT_TYPE

        file_id = str(uuid.uuid4())
        s3_key = f"users/{user_id}/{file_id}/{file_name}"
        now = int(time.time())
        ttl = int(os.environ.get("UPLOAD_URL_TTL_SECONDS", str(DEFAULT_UPLOAD_URL_TTL_SECONDS)))

        upload_url = _get_s3_client().generate_presigned_url(
            ClientMethod="put_object",
            Params={
                "Bucket": os.environ["S3_BUCKET"],
                "Key": s3_key,
                "ContentType": content_type,
            },
            ExpiresIn=ttl,
            HttpMethod="PUT",
        )

        get_files_table().put_item(
            Item={
                "userId": user_id,
                "fileId": file_id,
                "fileName": file_name,
                "s3Key": s3_key,
                "size": size,
                "contentType": content_type,
                "status": "pending",
                "uploadedAt": now,
            }
        )

        return json_response(
            200,
            {
                "fileId": file_id,
                "uploadUrl": upload_url,
                "expiresIn": ttl,
                "requiredHeaders": {
                    "Content-Type": content_type,
                    "Content-Length": str(size),
                },
            },
        )
    except Unauthorized as exc:
        return error_response(401, str(exc))
    except ValueError as exc:
        return error_response(400, str(exc))
    except Exception:
        logger.exception("Upload request failed")
        return error_response(500, "Internal server error")
