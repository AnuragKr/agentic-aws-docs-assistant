import os
from functools import lru_cache
from urllib.error import URLError
from urllib.request import Request, urlopen

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError, NoCredentialsError, ProfileNotFound

from config.logging import ConfigurationError

_BOTO_CONFIG = Config(retries={"max_attempts": 10, "mode": "adaptive"})
_CREDENTIAL_ENV_KEYS = (
    "AWS_ACCESS_KEY_ID",
    "AWS_SECRET_ACCESS_KEY",
    "AWS_SESSION_TOKEN",
    "AWS_SECURITY_TOKEN",
)


def sanitize_aws_environment() -> None:
    """Blank env vars block the EC2 instance-profile provider — remove them."""
    for key in _CREDENTIAL_ENV_KEYS:
        if not os.environ.get(key, "").strip():
            os.environ.pop(key, None)


def aws_credentials_help(region: str) -> str:
    ec2_hint = _ec2_instance_profile_hint()
    return (
        "AWS credentials are required for S3, DynamoDB, and OpenSearch (SigV4).\n"
        "Configure credentials using one of:\n"
        "  • EC2: IAM instance profile attached (terraform aws_instance.app)\n"
        "  • EC2: run as ubuntu — do NOT use sudo (sudo drops instance role)\n"
        "  • EC2: unset empty AWS_ACCESS_KEY_ID in shell profile and backend/.env\n"
        "  • Local: aws configure\n"
        "  • Local: export AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_SESSION_TOKEN\n"
        "  • SSO: aws sso login --profile YOUR_PROFILE && export AWS_PROFILE=YOUR_PROFILE\n"
        f"Region in .env: {region}\n"
        f"{ec2_hint}\n"
        "Diagnostics on EC2: uv run python scripts/check_aws.py"
    )


def _ec2_instance_profile_hint() -> str:
    profile = _imds_instance_profile_name()
    if profile:
        return f"EC2 instance profile detected: {profile}"
    return (
        "EC2 instance profile not visible via IMDS — attach "
        "aws_iam_instance_profile.ec2_profile or stop/start the instance."
    )


def _imds_instance_profile_name() -> str | None:
    try:
        token_request = Request(
            "http://169.254.169.254/latest/api/token",
            method="PUT",
            headers={"X-aws-ec2-metadata-token-ttl-seconds": "60"},
        )
        with urlopen(token_request, timeout=1) as response:
            token = response.read().decode()

        profile_request = Request(
            "http://169.254.169.254/latest/meta-data/iam/security-credentials/",
            headers={"X-aws-ec2-metadata-token": token},
        )
        with urlopen(profile_request, timeout=1) as response:
            name = response.read().decode().strip()
            return name or None
    except (URLError, OSError, TimeoutError):
        return None


@lru_cache(maxsize=4)
def get_boto_session(region: str) -> boto3.Session:
    sanitize_aws_environment()
    return boto3.Session(region_name=region)


def resolve_aws_credentials(region: str):
    """
    Resolve credentials from the default provider chain (env, profile, SSO, EC2 role).

    Some providers (SSO) only materialize credentials after the first API call.
    """
    session = get_boto_session(region)
    credentials = session.get_credentials()
    if credentials is not None and credentials.access_key:
        return credentials

    verify_aws_credentials(region)
    credentials = session.get_credentials()
    if credentials is None or not credentials.access_key:
        raise ConfigurationError(aws_credentials_help(region))
    return credentials


def verify_aws_credentials(region: str) -> dict:
    """Call STS to validate credentials and return caller identity."""
    session = get_boto_session(region)
    try:
        return session.client("sts", config=_BOTO_CONFIG).get_caller_identity()
    except (NoCredentialsError, ProfileNotFound) as exc:
        raise ConfigurationError(aws_credentials_help(region)) from exc
    except (ClientError, BotoCoreError) as exc:
        raise ConfigurationError(
            f"{aws_credentials_help(region)}\nUnderlying error: {exc}"
        ) from exc


def get_s3_client(region: str):
    return get_boto_session(region).client("s3", config=_BOTO_CONFIG)


def get_dynamodb_table(region: str, table_name: str):
    return get_boto_session(region).resource("dynamodb", config=_BOTO_CONFIG).Table(table_name)
