#!/usr/bin/env python3
"""Run on EC2 to verify instance profile, S3, DynamoDB, and OpenSearch access."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from config.settings import get_settings
from infrastructure.aws.session import (
    _ec2_instance_profile_hint,
    sanitize_aws_environment,
    verify_aws_credentials,
)
from infrastructure.opensearch.indexer import create_opensearch_client


def main() -> int:
    sanitize_aws_environment()
    settings = get_settings()
    print(f"AWS_REGION={settings.aws_region}")
    print(_ec2_instance_profile_hint())

    identity = verify_aws_credentials(settings.aws_region)
    print("STS OK:", identity.get("Arn"))

    from infrastructure.aws.session import get_boto_session

    session = get_boto_session(settings.aws_region)
    s3 = session.client("s3")
    s3.head_bucket(Bucket=settings.s3_raw_bucket)
    print(f"S3 OK: {settings.s3_raw_bucket}")

    dynamodb = session.client("dynamodb")
    dynamodb.describe_table(TableName=settings.dynamodb_registry_table)
    print(f"DynamoDB OK: {settings.dynamodb_registry_table}")

    client = create_opensearch_client(settings)
    exists = client.indices.exists(index=settings.opensearch_index)
    print(f"OpenSearch OK: host={settings.opensearch_host} index_exists={exists}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print("CHECK FAILED:", exc, file=sys.stderr)
        raise SystemExit(1) from exc
