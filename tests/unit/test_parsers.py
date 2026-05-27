from pathlib import Path

from app.ingestion.domain.document import RawDocument
from app.ingestion.parsers.registry import ParserRegistry


def test_markdown_parser_preserves_headings() -> None:
    text = Path(__file__).parent.parent.joinpath("fixtures/sample.md").read_text()
    doc = RawDocument(key="lambda/guide.md", content=text, extension=".md")
    parsed = ParserRegistry().parse(doc)
    assert "# AWS Lambda" in parsed.text or "AWS Lambda" in parsed.text


def test_html_parser_strips_scripts() -> None:
    doc = RawDocument(
        key="page.html",
        content="<html><script>x</script><body><p>Hello</p></body></html>",
        extension=".html",
    )
    parsed = ParserRegistry().parse(doc)
    assert "Hello" in parsed.text
    assert "x" not in parsed.text
