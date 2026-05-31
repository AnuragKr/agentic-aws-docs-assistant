from domain.models import RetrievedChunk
from retrieval.citations import attach_citations, build_citation


def test_build_citation_with_url() -> None:
    chunk = RetrievedChunk(
        chunk_id="c1",
        document_id="d1",
        content="text",
        score=0.9,
        title="Lambda Developer Guide",
        section="Configuration",
        subsection="Concurrency",
        source_url="https://docs.aws.amazon.com/lambda/concurrency.html",
    )
    citation = build_citation(chunk)
    assert "Lambda Developer Guide" in citation
    assert "Concurrency" in citation
    assert "docs.aws.amazon.com" in citation


def test_attach_citations() -> None:
    chunk = RetrievedChunk(
        chunk_id="c1",
        document_id="d1",
        content="text",
        score=0.5,
        title="Guide",
    )
    results = attach_citations([chunk])
    assert results[0].citation
