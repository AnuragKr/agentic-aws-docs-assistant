from domain.models import RetrievedChunk
from generation.prompt_builder import PromptBuilder, SYSTEM_PROMPT


def test_prompt_builder_includes_chunk_metadata() -> None:
    builder = PromptBuilder(context_max_tokens=2000)
    chunks = [
        RetrievedChunk(
            chunk_id="c1",
            document_id="d1",
            content="Use AWS Organizations for multi-account governance.",
            score=0.9,
            document_title="AWS Well-Architected Framework",
            section="Organization",
            page_number=17,
        )
    ]
    system, user = builder.build("How do I govern accounts?", chunks)
    assert system == SYSTEM_PROMPT
    assert "AWS Well-Architected Framework" in user
    assert "Organization" in user
    assert "Page: 17" in user
    assert "How do I govern accounts?" in user


def test_prompt_builder_respects_context_token_limit() -> None:
    builder = PromptBuilder(context_max_tokens=80)
    chunks = [
        RetrievedChunk(
            chunk_id=f"c{index}",
            document_id="d1",
            content=f"Sentence {index} about AWS Lambda scaling behavior in detail.",
            score=0.5,
            document_title="Lambda Guide",
            section=f"Section {index}",
        )
        for index in range(10)
    ]
    context = builder.build_context(chunks)
    assert context.count("Source:") >= 1
    assert context.count("Source:") < len(chunks)
