from generation.models import INSUFFICIENT_EVIDENCE_MESSAGE
from generation.service import GenerationService


def test_clean_answer_removes_appended_insufficient_message() -> None:
    answer = (
        "Amazon S3 provides durable object storage for many workloads.\n\n"
        f"{INSUFFICIENT_EVIDENCE_MESSAGE}"
    )
    cleaned = GenerationService._clean_answer(answer)
    assert INSUFFICIENT_EVIDENCE_MESSAGE not in cleaned
    assert "Amazon S3 provides durable object storage" in cleaned
