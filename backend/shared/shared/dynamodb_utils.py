import os

import boto3


def get_dynamodb_resource():
    return boto3.resource("dynamodb")


def get_users_table():
    return get_dynamodb_resource().Table(os.environ["USERS_TABLE"])


def get_files_table():
    return get_dynamodb_resource().Table(os.environ["FILES_TABLE"])
