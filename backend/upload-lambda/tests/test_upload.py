from conftest import auth_event, issue_test_token, load_lambda_module, response_body


def test_upload_requires_authorization(aws_resources):
    app = load_lambda_module("upload-lambda")

    response = app.request_upload_handler(
        {"headers": {}, "body": '{"fileName":"test.txt","contentType":"text/plain","size":12}'},
        None,
    )

    assert response["statusCode"] == 401


def test_upload_returns_presigned_url_and_creates_pending_file(aws_resources):
    app = load_lambda_module("upload-lambda")
    token = issue_test_token("user-1")

    response = app.request_upload_handler(
        auth_event(
            token,
            {"fileName": "test.txt", "contentType": "text/plain", "size": 12},
        ),
        None,
    )

    assert response["statusCode"] == 200
    body = response_body(response)
    assert body["fileId"]
    assert body["uploadUrl"].startswith("https://")
    assert body["requiredHeaders"] == {"Content-Type": "text/plain", "Content-Length": "12"}

    item = aws_resources["files_table"].get_item(Key={"userId": "user-1", "fileId": body["fileId"]})["Item"]
    assert item["fileName"] == "test.txt"
    assert item["s3Key"] == f"users/user-1/{body['fileId']}/test.txt"
    assert item["status"] == "pending"


def test_upload_presigned_url_uses_regional_s3_endpoint(aws_resources, monkeypatch):
    monkeypatch.setenv("AWS_REGION", "ap-south-1")
    app = load_lambda_module("upload-lambda")
    token = issue_test_token("user-1")

    response = app.request_upload_handler(
        auth_event(
            token,
            {"fileName": "test.txt", "contentType": "text/plain", "size": 12},
        ),
        None,
    )

    assert response["statusCode"] == 200
    body = response_body(response)
    assert body["uploadUrl"].startswith("https://file-bucket.s3.ap-south-1.amazonaws.com/")


def test_upload_rejects_file_names_with_paths(aws_resources):
    app = load_lambda_module("upload-lambda")
    token = issue_test_token("user-1")

    response = app.request_upload_handler(
        auth_event(token, {"fileName": "../secret.txt", "contentType": "text/plain", "size": 12}),
        None,
    )

    assert response["statusCode"] == 400
