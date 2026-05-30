from pathlib import Path

from app.core.config import Settings
from app.ingestion.chunking.hierarchical_chunker import HierarchicalChunker
from app.ingestion.domain.document import DocumentMetadata
from app.ingestion.preprocessors.pipeline import PreprocessorPipeline
from app.ingestion.domain.document import ParsedDocument


def test_hierarchical_chunks_have_metadata() -> None:
    text = Path(__file__).parent.parent.joinpath("fixtures/sample.md").read_text()
    preprocessed = PreprocessorPipeline().process(
        ParsedDocument(key="lambda/concurrency/reserved.md", text=text, extension=".md")
    )
    meta = DocumentMetadata(
        document_name="reserved.md",
        source_url="https://docs.aws.amazon.com/lambda/concurrency",
        service="Lambda",
        document_type="guide",
    )
    chunks = HierarchicalChunker(Settings()).chunk(preprocessed, meta)
    assert chunks
    assert chunks[0].chunk_id
    assert chunks[0].section_hierarchy or chunks[0].service
