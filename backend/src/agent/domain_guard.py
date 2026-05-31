import re

from domain.chat import ChatMessage
from generation.models import DOMAIN_REJECTION_MESSAGE

_AWS_TERMS = {
    "aws",
    "amazon web services",
    "well-architected",
    "well architected",
    "cloudformation",
    "cloudwatch",
    "s3",
    "ec2",
    "lambda",
    "rds",
    "dynamodb",
    "iam",
    "vpc",
    "eks",
    "ecs",
    "fargate",
    "sqs",
    "sns",
    "kms",
    "glue",
    "athena",
    "redshift",
    "aurora",
    "elasticache",
    "cloudfront",
    "route 53",
    "route53",
    "alb",
    "nlb",
    "elb",
    "api gateway",
    "apigateway",
    "bedrock",
    "sagemaker",
    "step functions",
    "eventbridge",
    "organizations",
    "control tower",
    "config",
    "guardduty",
    "security hub",
    "waf",
    "shield",
    "secrets manager",
    "ssm",
    "systems manager",
    "efs",
    "ebs",
    "fsx",
    "snowball",
    "direct connect",
    "transit gateway",
    "privatelink",
    "cloudtrail",
    "codepipeline",
    "codebuild",
    "codedeploy",
    "codecommit",
    "amplify",
    "app runner",
    "lightsail",
    "batch",
    "emr",
    "kinesis",
    "msk",
    "opensearch",
    "elasticsearch",
    "documentdb",
    "neptune",
    "timestream",
    "quicksight",
    "ses",
    "workspaces",
    "cognito",
    "sts",
    "sso",
    "identity center",
}

_OFF_TOPIC_PATTERNS = [
    re.compile(r"\bcapital of\b", re.I),
    re.compile(r"\bstock market\b", re.I),
    re.compile(r"\bexplain python\b", re.I),
    re.compile(r"\bpython programming\b", re.I),
    re.compile(r"\bkubernetes\b(?![\w-]*(?:aws|eks|fargate))", re.I),
    re.compile(r"\brecipe for\b", re.I),
    re.compile(r"\bweather in\b", re.I),
]

_FOLLOW_UP_HINTS = re.compile(
    r"\b(it|this|that|they|those|these|compare|difference|versus|vs\.?|how about)\b",
    re.I,
)


class AWSDomainGuardService:
    """Deterministic guardrail — AWS-only questions."""

    def evaluate(self, query: str, history: list[ChatMessage] | None = None) -> tuple[bool, str | None]:
        text = query.strip()
        if not text:
            return False, DOMAIN_REJECTION_MESSAGE

        normalized = text.lower()
        if any(pattern.search(normalized) for pattern in _OFF_TOPIC_PATTERNS):
            if not self._has_aws_context(normalized, history):
                return False, DOMAIN_REJECTION_MESSAGE

        if self._mentions_aws(normalized):
            return True, None

        if history and self._history_is_aws(history) and _FOLLOW_UP_HINTS.search(normalized):
            return True, None

        if history and self._history_is_aws(history) and len(normalized.split()) <= 12:
            return True, None

        return False, DOMAIN_REJECTION_MESSAGE

    @staticmethod
    def _mentions_aws(text: str) -> bool:
        return any(term in text for term in _AWS_TERMS)

    def _has_aws_context(self, text: str, history: list[ChatMessage] | None) -> bool:
        if self._mentions_aws(text):
            return True
        return self._history_is_aws(history or [])

    @staticmethod
    def _history_is_aws(history: list[ChatMessage]) -> bool:
        combined = " ".join(message.content for message in history[-6:]).lower()
        return any(term in combined for term in _AWS_TERMS)
