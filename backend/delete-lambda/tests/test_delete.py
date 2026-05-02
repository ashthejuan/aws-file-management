import pytest
from botocore.exceptions import ClientError

from conftest import auth_event, issue_test_token, load_lambda_module


def test_delete_requires_authorization(aws_resources):
    app = load_lambda_module("delete-lambda")

    response = app.delete_handler({"headers": {}, "pathParameters": {"fileId": "file-1"}}, None)

    assert response["statusCode"] == 401


def test_delete_removes_s3_object_and_dynamodb_row(aws_resources):
    app = load_lambda_module("delete-lambda")
    s3 = aws_resources["s3"]
    files_table = aws_resources["files_table"]
    s3_key = "users/user-1/file-1/test.txt"
    s3.put_object(Bucket="file-bucket", Key=s3_key, Body=b"hello")
    files_table.put_item(
        Item={
            "userId": "user-1",
            "fileId": "file-1",
            "fileName": "test.txt",
            "s3Key": s3_key,
            "size": 5,
            "contentType": "text/plain",
            "status": "pending",
            "uploadedAt": 100,
        }
    )
    token = issue_test_token("user-1")

    response = app.delete_handler(auth_event(token, path_parameters={"fileId": "file-1"}), None)

    assert response["statusCode"] == 204
    assert "Item" not in files_table.get_item(Key={"userId": "user-1", "fileId": "file-1"})
    with pytest.raises(ClientError):
        s3.head_object(Bucket="file-bucket", Key=s3_key)


def test_delete_returns_404_for_missing_file(aws_resources):
    app = load_lambda_module("delete-lambda")
    token = issue_test_token("user-1")

    response = app.delete_handler(auth_event(token, path_parameters={"fileId": "missing"}), None)

    assert response["statusCode"] == 404
