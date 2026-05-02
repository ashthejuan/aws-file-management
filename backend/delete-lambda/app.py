import logging
import os
from typing import Any

import boto3

from shared.auth import Unauthorized, require_auth
from shared.dynamodb_utils import get_files_table
from shared.responses import error_response, json_response


logger = logging.getLogger(__name__)


def _get_s3_client():
    return boto3.client("s3")


def _get_file_id(event: dict[str, Any]) -> str:
    file_id = (event.get("pathParameters") or {}).get("fileId", "").strip()
    if not file_id:
        raise ValueError("fileId path parameter is required")
    return file_id


def delete_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    try:
        user_id = require_auth(event)
        file_id = _get_file_id(event)
        files_table = get_files_table()

        response = files_table.get_item(Key={"userId": user_id, "fileId": file_id})
        item = response.get("Item")
        if item is None:
            return error_response(404, "File not found")

        _get_s3_client().delete_object(Bucket=os.environ["S3_BUCKET"], Key=item["s3Key"])
        files_table.delete_item(Key={"userId": user_id, "fileId": file_id})

        return json_response(204)
    except Unauthorized as exc:
        return error_response(401, str(exc))
    except ValueError as exc:
        return error_response(400, str(exc))
    except Exception:
        logger.exception("Delete file failed")
        return error_response(500, "Internal server error")
