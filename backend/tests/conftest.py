import importlib.util
import json
import sys
from pathlib import Path

import boto3
import fakeredis
import pytest
from moto import mock_aws


BACKEND_DIR = Path(__file__).resolve().parents[1]
SHARED_DIR = BACKEND_DIR / "shared"

if str(SHARED_DIR) not in sys.path:
    sys.path.insert(0, str(SHARED_DIR))


@pytest.fixture(autouse=True)
def test_env(monkeypatch):
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
    monkeypatch.setenv("AWS_SECURITY_TOKEN", "testing")
    monkeypatch.setenv("AWS_SESSION_TOKEN", "testing")
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")
    monkeypatch.setenv("JWT_SECRET", "test-secret-that-is-long-enough-for-local-tests")
    monkeypatch.setenv("JWT_TTL_SECONDS", "3600")
    monkeypatch.setenv("USERS_TABLE", "Users")
    monkeypatch.setenv("FILES_TABLE", "Files")
    monkeypatch.setenv("S3_BUCKET", "file-bucket")
    monkeypatch.setenv("REDIS_ENDPOINT", "localhost")
    monkeypatch.setenv("REDIS_PORT", "6379")
    monkeypatch.setenv("UPLOAD_URL_TTL_SECONDS", "300")
    monkeypatch.setenv("MAX_UPLOAD_BYTES", str(50 * 1024 * 1024))

    import shared.redis_utils as redis_utils

    redis_utils.redis_client = fakeredis.FakeRedis(decode_responses=True)
    yield
    redis_utils.redis_client = None


@pytest.fixture
def aws_resources():
    with mock_aws():
        dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
        users_table = dynamodb.create_table(
            TableName="Users",
            KeySchema=[{"AttributeName": "userId", "KeyType": "HASH"}],
            AttributeDefinitions=[
                {"AttributeName": "userId", "AttributeType": "S"},
                {"AttributeName": "email", "AttributeType": "S"},
            ],
            GlobalSecondaryIndexes=[
                {
                    "IndexName": "EmailIndex",
                    "KeySchema": [{"AttributeName": "email", "KeyType": "HASH"}],
                    "Projection": {"ProjectionType": "ALL"},
                }
            ],
            BillingMode="PAY_PER_REQUEST",
        )
        files_table = dynamodb.create_table(
            TableName="Files",
            KeySchema=[
                {"AttributeName": "userId", "KeyType": "HASH"},
                {"AttributeName": "fileId", "KeyType": "RANGE"},
            ],
            AttributeDefinitions=[
                {"AttributeName": "userId", "AttributeType": "S"},
                {"AttributeName": "fileId", "AttributeType": "S"},
            ],
            BillingMode="PAY_PER_REQUEST",
        )

        users_table.wait_until_exists()
        files_table.wait_until_exists()

        s3 = boto3.client("s3", region_name="us-east-1")
        s3.create_bucket(Bucket="file-bucket")

        yield {
            "dynamodb": dynamodb,
            "users_table": users_table,
            "files_table": files_table,
            "s3": s3,
        }


def load_lambda_module(lambda_dir: str):
    module_name = f"{lambda_dir.replace('-', '_')}_app"
    sys.modules.pop(module_name, None)
    module_path = BACKEND_DIR / lambda_dir / "app.py"
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def json_event(body: dict, headers: dict | None = None) -> dict:
    return {"body": json.dumps(body), "headers": headers or {}}


def auth_event(token: str, body: dict | None = None, path_parameters: dict | None = None) -> dict:
    event = {
        "headers": {"Authorization": f"Bearer {token}"},
        "pathParameters": path_parameters or {},
    }
    if body is not None:
        event["body"] = json.dumps(body)
    return event


def response_body(response: dict):
    return json.loads(response["body"] or "{}")


def issue_test_token(user_id: str) -> str:
    from shared.jwt_utils import generate_jwt
    from shared.redis_utils import cache_jwt

    token, ttl = generate_jwt(user_id)
    cache_jwt(token, user_id, ttl)
    return token
