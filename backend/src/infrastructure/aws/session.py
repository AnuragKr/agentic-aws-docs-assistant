from functools import lru_cache

import boto3
from botocore.config import Config

_BOTO_CONFIG = Config(retries={"max_attempts": 10, "mode": "adaptive"})


@lru_cache(maxsize=4)
def get_boto_session(region: str) -> boto3.Session:
    return boto3.Session(region_name=region)


def get_s3_client(region: str):
    return get_boto_session(region).client("s3", config=_BOTO_CONFIG)


def get_dynamodb_table(region: str, table_name: str):
    return get_boto_session(region).resource("dynamodb", config=_BOTO_CONFIG).Table(table_name)
