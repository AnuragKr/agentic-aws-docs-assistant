from config.settings import Settings
from config.token_utils import count_tokens, get_token_encoder
from ingestion.chunkers.sentence_splitter import build_sentence_chunks, split_into_sentences


def test_split_into_sentences_respects_punctuation() -> None:
    text = "AWS Lambda scales automatically. It runs your code on demand. Use IAM for access."
    sentences = split_into_sentences(text)
    assert len(sentences) == 3
    assert sentences[0].endswith(".")


def test_small_section_stays_single_chunk() -> None:
    encoder = get_token_encoder()
    text = "Short section with one idea. It fits easily."
    chunks = build_sentence_chunks(
        text,
        target_tokens=800,
        min_tokens=500,
        max_tokens=1200,
        overlap_tokens=100,
        encoder=encoder,
    )
    assert len(chunks) == 1
    assert "Short section" in chunks[0]


def test_never_splits_mid_sentence() -> None:
    encoder = get_token_encoder()
    sentences = [
        "Amazon S3 provides durable object storage for cloud workloads.",
        "AWS IAM controls who can access your AWS resources securely.",
        "CloudTrail records API activity for auditing and compliance reviews.",
        "Organizations helps you manage multiple accounts centrally at scale.",
        "AWS Config tracks resource configuration changes over time consistently.",
    ]
    text = " ".join(sentences)
    chunks = build_sentence_chunks(
        text,
        target_tokens=25,
        min_tokens=15,
        max_tokens=45,
        overlap_tokens=8,
        encoder=encoder,
    )
    assert len(chunks) >= 2
    for chunk in chunks:
        for sentence in sentences:
            fragment = sentence[:30]
            if fragment in chunk:
                assert sentence in chunk, f"Partial sentence found in chunk: {chunk!r}"


def test_overlap_uses_complete_sentences() -> None:
    encoder = get_token_encoder()
    sentences = [f"Sentence number {index} about AWS services." for index in range(12)]
    text = " ".join(sentences)
    chunks = build_sentence_chunks(
        text,
        target_tokens=35,
        min_tokens=20,
        max_tokens=70,
        overlap_tokens=15,
        encoder=encoder,
    )
    assert len(chunks) >= 2
    first_tail = chunks[0].split()[-4:]
    assert any(word in chunks[1] for word in first_tail if len(word) > 3)


def test_hierarchical_chunker_preserves_sentence_boundaries() -> None:
    from datetime import datetime, timezone

    from domain.models import PreprocessedDocument, SectionNode
    from ingestion.chunkers.hierarchical import HierarchicalChunker
    from ingestion.enrichers.metadata import MetadataExtractor

    settings = Settings(
        CHUNK_MIN_TOKENS=20,
        CHUNK_TARGET_TOKENS=50,
        CHUNK_MAX_TOKENS=100,
        CHUNK_OVERLAP_TOKENS=10,
    )
    sentence = "This is a complete sentence about AWS Lambda scaling."
    content = " ".join([f"{sentence} Variant {index}." for index in range(8)])
    doc = PreprocessedDocument(
        key="lambda/guide.md",
        text=content,
        extension=".md",
        etag="1",
        last_modified=datetime.now(timezone.utc),
        sections=[SectionNode(title="Guide", level=1, content=content)],
    )
    metadata = MetadataExtractor(settings).extract(doc)
    chunks = HierarchicalChunker(settings).chunk(doc, metadata)
    for chunk in chunks:
        assert chunk.content.count("Variant") == 0 or chunk.content.endswith(".")


def test_oversized_single_sentence_kept_intact() -> None:
    encoder = get_token_encoder()
    long_sentence = "Word " * 400 + "end."
    chunks = build_sentence_chunks(
        long_sentence,
        target_tokens=50,
        min_tokens=20,
        max_tokens=100,
        overlap_tokens=0,
        encoder=encoder,
    )
    assert len(chunks) == 1
    assert chunks[0] == long_sentence.strip()
    assert count_tokens(chunks[0], encoder) > 100
