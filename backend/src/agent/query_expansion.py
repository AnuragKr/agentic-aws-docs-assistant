import re

from config.logging import get_logger
from config.settings import Settings

logger = get_logger(__name__)

_AWS_EXPANSIONS: dict[str, list[str]] = {
    "s3": [
        "Amazon S3 security",
        "S3 encryption best practices",
        "S3 bucket policy security",
        "S3 access control",
        "AWS Well-Architected S3 security",
    ],
    "lambda": [
        "AWS Lambda best practices",
        "Lambda function security",
        "Lambda IAM permissions",
        "Lambda scaling configuration",
    ],
    "ec2": [
        "Amazon EC2 security groups",
        "EC2 instance best practices",
        "EC2 networking AWS",
    ],
    "iam": [
        "AWS IAM best practices",
        "IAM least privilege",
        "IAM roles and policies",
    ],
    "vpc": [
        "Amazon VPC networking",
        "VPC security best practices",
        "VPC subnets and routing",
    ],
    "rds": [
        "Amazon RDS security",
        "RDS encryption at rest",
        "RDS backup best practices",
    ],
    "efs": [
        "Amazon EFS storage",
        "EFS security best practices",
        "EFS vs S3 comparison",
    ],
    "eks": [
        "Amazon EKS best practices",
        "EKS security configuration",
        "EKS networking AWS",
    ],
}

_SECURITY_SUFFIXES = [
    "security best practices",
    "encryption",
    "access control",
    "Well-Architected security",
]


class QueryExpansionService:
    """Generate up to N search phrases from the rewritten query."""

    def __init__(self, settings: Settings) -> None:
        self._max_expansions = settings.max_query_expansions

    def expand(self, query: str) -> list[str]:
        query = query.strip()
        if not query:
            return []

        expansions: list[str] = [query]
        lower = query.lower()

        for key, phrases in _AWS_EXPANSIONS.items():
            if key in lower or f"amazon {key}" in lower:
                for phrase in phrases:
                    if phrase not in expansions:
                        expansions.append(phrase)
                    if len(expansions) >= self._max_expansions:
                        break
            if len(expansions) >= self._max_expansions:
                break

        if len(expansions) < self._max_expansions and re.search(r"\bsecure\b|\bsecurity\b", lower):
            for suffix in _SECURITY_SUFFIXES:
                candidate = f"{query} {suffix}".strip()
                if candidate not in expansions:
                    expansions.append(candidate)
                if len(expansions) >= self._max_expansions:
                    break

        if len(expansions) < self._max_expansions:
            aws_variant = query if lower.startswith("aws") or "amazon" in lower else f"AWS {query}"
            if aws_variant not in expansions:
                expansions.append(aws_variant)

        result = expansions[: self._max_expansions]
        logger.info("query_expanded", count=len(result))
        return result
