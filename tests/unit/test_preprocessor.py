from pathlib import Path

from app.ingestion.domain.document import ParsedDocument
from app.ingestion.preprocessors.pipeline import PreprocessorPipeline


def test_section_detection() -> None:
    text = Path(__file__).parent.parent.joinpath("fixtures/sample.md").read_text()
    doc = ParsedDocument(key="lambda/guide.md", text=text, extension=".md")
    result = PreprocessorPipeline().process(doc)
    assert len(result.sections) >= 2
    assert any(s.title == "Concurrency" for s in result.sections)
