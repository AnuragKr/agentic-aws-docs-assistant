from agent.domain_guard import AWSDomainGuardService
from domain.chat import ChatMessage
from generation.models import DOMAIN_REJECTION_MESSAGE


def test_domain_guard_allows_aws_query() -> None:
    guard = AWSDomainGuardService()
    allowed, message = guard.evaluate("How do I secure S3 buckets?")
    assert allowed is True
    assert message is None


def test_domain_guard_rejects_off_topic() -> None:
    guard = AWSDomainGuardService()
    allowed, message = guard.evaluate("What is the capital of France?")
    assert allowed is False
    assert message == DOMAIN_REJECTION_MESSAGE


def test_domain_guard_allows_follow_up_with_aws_history() -> None:
    guard = AWSDomainGuardService()
    history = [ChatMessage(role="user", content="What is S3?")]
    allowed, message = guard.evaluate("How does it compare to EFS?", history)
    assert allowed is True
    assert message is None
