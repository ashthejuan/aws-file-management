from conftest import auth_event, issue_test_token, load_lambda_module, response_body


def test_list_requires_authorization(aws_resources):
    app = load_lambda_module("list-lambda")

    response = app.list_handler({"headers": {}}, None)

    assert response["statusCode"] == 401


def test_list_returns_only_callers_files_sorted_newest_first(aws_resources):
    app = load_lambda_module("list-lambda")
    files_table = aws_resources["files_table"]
    files_table.put_item(
        Item={
            "userId": "user-1",
            "fileId": "old",
            "fileName": "old.txt",
            "s3Key": "users/user-1/old/old.txt",
            "size": 1,
            "contentType": "text/plain",
            "status": "pending",
            "uploadedAt": 100,
        }
    )
    files_table.put_item(
        Item={
            "userId": "user-1",
            "fileId": "new",
            "fileName": "new.txt",
            "s3Key": "users/user-1/new/new.txt",
            "size": 2,
            "contentType": "text/plain",
            "status": "pending",
            "uploadedAt": 200,
        }
    )
    files_table.put_item(
        Item={
            "userId": "user-2",
            "fileId": "other",
            "fileName": "other.txt",
            "s3Key": "users/user-2/other/other.txt",
            "size": 3,
            "contentType": "text/plain",
            "status": "pending",
            "uploadedAt": 300,
        }
    )

    token = issue_test_token("user-1")
    response = app.list_handler(auth_event(token), None)

    assert response["statusCode"] == 200
    body = response_body(response)
    assert [item["fileId"] for item in body] == ["new", "old"]
    assert {item["fileName"] for item in body} == {"new.txt", "old.txt"}
