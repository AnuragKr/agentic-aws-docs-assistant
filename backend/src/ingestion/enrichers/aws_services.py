"""Deterministic AWS service name detection from document text."""

import re
from difflib import SequenceMatcher

# Canonical display name → regex patterns (exact match, word boundaries)
AWS_SERVICE_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("AWS IAM", re.compile(r"\bIAM\b|\bIdentity and Access Management\b", re.I)),
    ("AWS CloudTrail", re.compile(r"\bCloudTrail\b|\bAWS CloudTrail\b", re.I)),
    ("AWS Organizations", re.compile(r"\bAWS Organizations\b|\bOrganizations\b", re.I)),
    ("AWS KMS", re.compile(r"\bAWS KMS\b|\bKey Management Service\b|\bKMS\b", re.I)),
    ("Amazon S3", re.compile(r"\bAmazon S3\b|\bAmazon Simple Storage Service\b|\bS3\b", re.I)),
    ("Amazon EC2", re.compile(r"\bAmazon EC2\b|\bAmazon Elastic Compute Cloud\b|\bEC2\b", re.I)),
    ("AWS Lambda", re.compile(r"\bAWS Lambda\b|\bLambda functions?\b", re.I)),
    ("Amazon VPC", re.compile(r"\bAmazon VPC\b|\bVirtual Private Cloud\b|\bVPC\b", re.I)),
    ("Amazon CloudWatch", re.compile(r"\bAmazon CloudWatch\b|\bCloudWatch\b", re.I)),
    ("Amazon RDS", re.compile(r"\bAmazon RDS\b|\bAmazon Relational Database Service\b|\bRDS\b", re.I)),
    ("Amazon DynamoDB", re.compile(r"\bAmazon DynamoDB\b|\bDynamoDB\b", re.I)),
    ("Amazon GuardDuty", re.compile(r"\bAmazon GuardDuty\b|\bGuardDuty\b", re.I)),
    ("AWS Security Hub", re.compile(r"\bAWS Security Hub\b|\bSecurity Hub\b", re.I)),
    ("AWS Config", re.compile(r"\bAWS Config\b|\bAmazon Config\b", re.I)),
    ("AWS Secrets Manager", re.compile(r"\bAWS Secrets Manager\b|\bSecrets Manager\b", re.I)),
    ("AWS WAF", re.compile(r"\bAWS WAF\b|\bAmazon WAF\b|\bWAF\b", re.I)),
    ("AWS Shield", re.compile(r"\bAWS Shield\b|\bShield Advanced\b", re.I)),
    ("Amazon CloudFront", re.compile(r"\bAmazon CloudFront\b|\bCloudFront\b", re.I)),
    ("Amazon Route 53", re.compile(r"\bAmazon Route 53\b|\bRoute 53\b", re.I)),
    ("Amazon EKS", re.compile(r"\bAmazon EKS\b|\bElastic Kubernetes Service\b|\bEKS\b", re.I)),
    ("Amazon ECS", re.compile(r"\bAmazon ECS\b|\bElastic Container Service\b|\bECS\b", re.I)),
    ("Amazon SNS", re.compile(r"\bAmazon SNS\b|\bSimple Notification Service\b|\bSNS\b", re.I)),
    ("Amazon SQS", re.compile(r"\bAmazon SQS\b|\bSimple Queue Service\b|\bSQS\b", re.I)),
    ("Amazon EventBridge", re.compile(r"\bAmazon EventBridge\b|\bEventBridge\b", re.I)),
    ("AWS STS", re.compile(r"\bAWS STS\b|\bSecurity Token Service\b|\bSTS\b", re.I)),
    ("Amazon Cognito", re.compile(r"\bAmazon Cognito\b|\bCognito\b", re.I)),
    ("Amazon Macie", re.compile(r"\bAmazon Macie\b|\bMacie\b", re.I)),
    ("Amazon Inspector", re.compile(r"\bAmazon Inspector\b|\bInspector\b", re.I)),
    ("Amazon Detective", re.compile(r"\bAmazon Detective\b|\bDetective\b", re.I)),
    ("IAM Access Analyzer", re.compile(r"\bIAM Access Analyzer\b|\bAccess Analyzer\b", re.I)),
    ("AWS Control Tower", re.compile(r"\bAWS Control Tower\b|\bControl Tower\b", re.I)),
    ("AWS CloudFormation", re.compile(r"\bAWS CloudFormation\b|\bCloudFormation\b", re.I)),
    ("AWS Systems Manager", re.compile(r"\bAWS Systems Manager\b|\bSystems Manager\b|\bSSM\b", re.I)),
    ("AWS Backup", re.compile(r"\bAWS Backup\b", re.I)),
    ("AWS Audit Manager", re.compile(r"\bAWS Audit Manager\b|\bAudit Manager\b", re.I)),
    ("Amazon OpenSearch Service", re.compile(r"\bAmazon OpenSearch Service\b|\bOpenSearch Service\b", re.I)),
    ("AWS Artifact", re.compile(r"\bAWS Artifact\b", re.I)),
    ("AWS Certificate Manager", re.compile(r"\bAWS Certificate Manager\b|\bACM\b", re.I)),
    ("AWS Network Firewall", re.compile(r"\bAWS Network Firewall\b|\bNetwork Firewall\b", re.I)),
    ("Amazon ElastiCache", re.compile(r"\bAmazon ElastiCache\b|\bElastiCache\b", re.I)),
    ("Amazon Redshift", re.compile(r"\bAmazon Redshift\b|\bRedshift\b", re.I)),
    ("AWS Glue", re.compile(r"\bAWS Glue\b|\bGlue\b", re.I)),
    ("Amazon Athena", re.compile(r"\bAmazon Athena\b|\bAthena\b", re.I)),
    ("AWS Step Functions", re.compile(r"\bAWS Step Functions\b|\bStep Functions\b", re.I)),
    ("Amazon API Gateway", re.compile(r"\bAmazon API Gateway\b|\bAPI Gateway\b", re.I)),
    ("AWS AppSync", re.compile(r"\bAWS AppSync\b|\bAppSync\b", re.I)),
    ("Amazon Bedrock", re.compile(r"\bAmazon Bedrock\b|\bBedrock\b", re.I)),
    ("AWS Fargate", re.compile(r"\bAWS Fargate\b|\bFargate\b", re.I)),
    ("AWS Batch", re.compile(r"\bAWS Batch\b", re.I)),
    ("Amazon ECR", re.compile(r"\bAmazon ECR\b|\bElastic Container Registry\b|\bECR\b", re.I)),
    ("AWS Direct Connect", re.compile(r"\bAWS Direct Connect\b|\bDirect Connect\b", re.I)),
    ("AWS Transit Gateway", re.compile(r"\bAWS Transit Gateway\b|\bTransit Gateway\b", re.I)),
    ("AWS PrivateLink", re.compile(r"\bAWS PrivateLink\b|\bPrivateLink\b", re.I)),
    ("AWS Global Accelerator", re.compile(r"\bAWS Global Accelerator\b|\bGlobal Accelerator\b", re.I)),
    ("AWS Resource Access Manager", re.compile(r"\bAWS Resource Access Manager\b|\bRAM\b", re.I)),
    ("AWS Service Catalog", re.compile(r"\bAWS Service Catalog\b|\bService Catalog\b", re.I)),
    ("AWS Trusted Advisor", re.compile(r"\bAWS Trusted Advisor\b|\bTrusted Advisor\b", re.I)),
    ("AWS Well-Architected Tool", re.compile(r"\bAWS Well-Architected Tool\b|\bWell-Architected Tool\b", re.I)),
]

_AWS_SERVICE_CATALOG = [name for name, _ in AWS_SERVICE_PATTERNS]
_FUZZY_MIN_RATIO = 0.88


def detect_aws_services(text: str) -> list[str]:
    """Return sorted unique AWS service names found via exact and fuzzy matching."""
    found: set[str] = set()
    for name, pattern in AWS_SERVICE_PATTERNS:
        if pattern.search(text):
            found.add(name)

    for token in _candidate_tokens(text):
        match = _fuzzy_match_service(token)
        if match:
            found.add(match)

    return sorted(found)


def _candidate_tokens(text: str) -> list[str]:
    tokens: set[str] = set()
    for match in re.finditer(r"\b[A-Z][A-Za-z0-9]+(?:\s+[A-Z][A-Za-z0-9]+){0,4}\b", text):
        value = match.group(0).strip()
        if len(value) >= 3:
            tokens.add(value)
    return sorted(tokens)


def _fuzzy_match_service(token: str) -> str | None:
    token_lower = token.lower()
    for service in _AWS_SERVICE_CATALOG:
        service_tail = service.split()[-1].lower()
        if token_lower == service_tail:
            return service
        if SequenceMatcher(None, token_lower, service.lower()).ratio() >= _FUZZY_MIN_RATIO:
            return service
    return None
