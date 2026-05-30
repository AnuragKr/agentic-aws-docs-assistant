from datetime import datetime, timezone

from domain.models import ParsedDocument, SectionNode
from ingestion.preprocessors.pipeline import DocumentPreprocessor


def test_preprocessor_preserves_docling_sections() -> None:
    parsed = ParsedDocument(
        key="lambda/guide.md",
        text="# Lambda\n\nIntro",
        extension=".md",
        etag="1",
        last_modified=datetime.now(timezone.utc),
        sections=[SectionNode(title="Lambda", level=1, content="Intro")],
    )
    doc = DocumentPreprocessor().process(parsed)
    assert len(doc.sections) == 1
    assert doc.sections[0].title == "Lambda"
