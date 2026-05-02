from boto3.dynamodb.conditions import Key

from conftest import json_event, load_lambda_module, response_body


def test_signup_creates_user_hashes_password_and_caches_token(aws_resources):
    app = load_lambda_module("auth-lambda")

    response = app.signup_handler(
        json_event({"email": "User@Example.com", "password": "password123"}),
        None,
    )

    assert response["statusCode"] == 201
    body = response_body(response)
    assert body["token"]
    assert body["expiresIn"] == 3600

    users = aws_resources["users_table"].query(
        IndexName="EmailIndex",
        KeyConditionExpression=Key("email").eq("user@example.com"),
    )["Items"]
    assert len(users) == 1
    assert users[0]["passwordHash"] != "password123"

    from shared.redis_utils import get_cached_user_id

    assert get_cached_user_id(body["token"]) == users[0]["userId"]


def test_login_returns_cached_jwt_for_valid_credentials(aws_resources):
    app = load_lambda_module("auth-lambda")
    app.signup_handler(json_event({"email": "user@example.com", "password": "password123"}), None)

    response = app.login_handler(json_event({"email": "user@example.com", "password": "password123"}), None)

    assert response["statusCode"] == 200
    body = response_body(response)
    assert body["token"]

    from shared.jwt_utils import decode_jwt
    from shared.redis_utils import get_cached_user_id

    payload = decode_jwt(body["token"])
    assert get_cached_user_id(body["token"]) == payload["sub"]


def test_login_rejects_wrong_password(aws_resources):
    app = load_lambda_module("auth-lambda")
    app.signup_handler(json_event({"email": "user@example.com", "password": "password123"}), None)

    response = app.login_handler(json_event({"email": "user@example.com", "password": "wrong-password"}), None)

    assert response["statusCode"] == 401


def test_signup_rejects_duplicate_email(aws_resources):
    app = load_lambda_module("auth-lambda")
    event = json_event({"email": "user@example.com", "password": "password123"})
    app.signup_handler(event, None)

    response = app.signup_handler(event, None)

    assert response["statusCode"] == 409
