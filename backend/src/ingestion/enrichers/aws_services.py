"""Deterministic AWS service name detection from document text."""

import re

# Canonical service name → regex patterns (word boundaries)
AWS_SERVICE_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("IAM", re.compile(r"\bIAM\b|\bIdentity and Access Management\b", re.I)),
    ("CloudTrail", re.compile(r"\bCloudTrail\b", re.I)),
    ("Organizations", re.compile(r"\bAWS Organizations\b|\bOrganizations\b", re.I)),
    ("KMS", re.compile(r"\bAWS KMS\b|\bKey Management Service\b|\bKMS\b", re.I)),
    ("S3", re.compile(r"\bAmazon S3\b|\bAmazon Simple Storage Service\b|\bS3\b", re.I)),
    ("EC2", re.compile(r"\bAmazon EC2\b|\bAmazon Elastic Compute Cloud\b|\bEC2\b", re.I)),
    ("Lambda", re.compile(r"\bAWS Lambda\b|\bLambda\b", re.I)),
    ("VPC", re.compile(r"\bAmazon VPC\b|\bVirtual Private Cloud\b|\bVPC\b", re.I)),
    ("CloudWatch", re.compile(r"\bAmazon CloudWatch\b|\bCloudWatch\b", re.I)),
    ("RDS", re.compile(r"\bAmazon RDS\b|\bAmazon Relational Database Service\b|\bRDS\b", re.I)),
    ("DynamoDB", re.compile(r"\bAmazon DynamoDB\b|\bDynamoDB\b", re.I)),
    ("GuardDuty", re.compile(r"\bAmazon GuardDuty\b|\bGuardDuty\b", re.I)),
    ("Security Hub", re.compile(r"\bAWS Security Hub\b|\bSecurity Hub\b", re.I)),
    ("Config", re.compile(r"\bAWS Config\b|\bAmazon Config\b", re.I)),
    ("Secrets Manager", re.compile(r"\bAWS Secrets Manager\b|\bSecrets Manager\b", re.I)),
    ("WAF", re.compile(r"\bAWS WAF\b|\bAmazon WAF\b|\bWAF\b", re.I)),
    ("Shield", re.compile(r"\bAWS Shield\b|\bShield Advanced\b", re.I)),
    ("CloudFront", re.compile(r"\bAmazon CloudFront\b|\bCloudFront\b", re.I)),
    ("Route 53", re.compile(r"\bAmazon Route 53\b|\bRoute 53\b", re.I)),
    ("EKS", re.compile(r"\bAmazon EKS\b|\bElastic Kubernetes Service\b|\bEKS\b", re.I)),
    ("ECS", re.compile(r"\bAmazon ECS\b|\bElastic Container Service\b|\bECS\b", re.I)),
    ("SNS", re.compile(r"\bAmazon SNS\b|\bSimple Notification Service\b|\bSNS\b", re.I)),
    ("SQS", re.compile(r"\bAmazon SQS\b|\bSimple Queue Service\b|\bSQS\b", re.I)),
    ("EventBridge", re.compile(r"\bAmazon EventBridge\b|\bEventBridge\b", re.I)),
    ("STS", re.compile(r"\bAWS STS\b|\bSecurity Token Service\b|\bSTS\b", re.I)),
    ("Cognito", re.compile(r"\bAmazon Cognito\b|\bCognito\b", re.I)),
    ("Macie", re.compile(r"\bAmazon Macie\b|\bMacie\b", re.I)),
    ("Inspector", re.compile(r"\bAmazon Inspector\b|\bInspector\b", re.I)),
    ("Detective", re.compile(r"\bAmazon Detective\b|\bDetective\b", re.I)),
    ("Access Analyzer", re.compile(r"\bIAM Access Analyzer\b|\bAccess Analyzer\b", re.I)),
]


def detect_aws_services(text: str) -> list[str]:
    """Return sorted unique AWS service names found in text."""
    found: set[str] = set()
    for name, pattern in AWS_SERVICE_PATTERNS:
        if pattern.search(text):
            found.add(name)
    return sorted(found)
