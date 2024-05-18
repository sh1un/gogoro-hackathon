import os

import boto3

# Set up boto3 client for SSM
ssm = boto3.client("ssm")


def get_opensearch_endpoint():
    parameter = ssm.get_parameter(Name="OPENSEARCH_ENDPOINT", WithDecryption=True)
    return parameter["Parameter"]["Value"]


def get_opensearch_username():
    parameter = ssm.get_parameter(Name="OPENSEARCH_USERNAME", WithDecryption=True)
    return parameter["Parameter"]["Value"]


def get_opensearch_password():
    parameter = ssm.get_parameter(Name="OPENSEARCH_PASSWORD", WithDecryption=True)
    return parameter["Parameter"]["Value"]


def get_langchain_api_key():
    parameter = ssm.get_parameter(Name="LANGCHAIN_API_KEY", WithDecryption=True)
    return parameter["Parameter"]["Value"]


def set_environment_variable(key: str, value: str):
    os.environ[key] = value
