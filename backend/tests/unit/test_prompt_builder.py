from domain.models import RetrievedChunk
from generation.intent_prompts import build_system_prompt
from generation.prompt_builder import PromptBuilder

from domain.intent import QueryIntent


def test_prompt_builder_uses_compare_structure() -> None:
    builder = PromptBuilder(context_max_tokens=2000)
    chunks = [
        RetrievedChunk(
            chunk_id="c1",
            document_id="d1",
            content="Amazon S3 is object storage.",
            score=0.9,
            document_title="S3 Guide",
            section="Overview",
            page_number=17,
        )
    ]
    system, user = builder.build("Compare S3 and EFS", chunks, intent=QueryIntent.COMPARE)
    assert "COMPARISON" in system
    assert "Comparison Table" in system
    assert "S3 Guide" in user
    assert "Page: 17" in user
    assert "Compare S3 and EFS" in user


def test_prompt_builder_omits_page_when_missing() -> None:
    builder = PromptBuilder(context_max_tokens=2000)
    chunks = [
        RetrievedChunk(
            chunk_id="c1",
            document_id="d1",
            content="Amazon EFS provides file storage.",
            score=0.9,
            document_title="EFS Guide",
            section="Overview",
        )
    ]
    _, user = builder.build("What is EFS?", chunks, intent=QueryIntent.EXPLAIN)
    assert "Page:" not in user


def test_build_system_prompt_explain_contains_sections() -> None:
    system = build_system_prompt(QueryIntent.EXPLAIN)
    assert "Overview" in system
    assert "Key Features" in system
