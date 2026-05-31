from datetime import datetime, timezone

from domain.models import RawDocument
from ingestion.parsers.factory import ParserFactory
from ingestion.parsers.hierarchy import extract_hierarchy_from_text
from ingestion.parsers.text import TextParser


def test_text_parser_for_txt_files() -> None:
    raw = RawDocument(
        key="lambda/notes.txt",
        content="Plain text content",
        extension=".txt",
        etag="1",
        last_modified=datetime.now(timezone.utc),
    )
    parsed = TextParser().parse(raw)
    assert "Plain text" in parsed.text


def test_parser_factory_routes_txt_to_text_parser() -> None:
    raw = RawDocument(
        key="lambda/notes.txt",
        content="Notes",
        extension=".txt",
        etag="1",
        last_modified=datetime.now(timezone.utc),
    )
    parsed = ParserFactory().parse(raw)
    assert parsed.text == "Notes"


def test_markdown_hierarchy_builds_section_tree() -> None:
    text = "# Lambda\n\nIntro paragraph.\n\n## Concurrency\n\nDetails here."
    sections = extract_hierarchy_from_text(text)
    assert len(sections) == 1
    assert sections[0].title == "Lambda"
    assert sections[0].content.startswith("Intro")
    assert any(child.title == "Concurrency" for child in sections[0].children)


def test_pdf_hierarchy_uses_font_sizes() -> None:
    from ingestion.parsers.hierarchy import extract_hierarchy_from_pdf_lines

    lines = [
        ("Lambda", 18.0),
        ("Intro paragraph.", 11.0),
        ("Concurrency", 14.0),
        ("Concurrency details.", 11.0),
    ]
    sections = extract_hierarchy_from_pdf_lines(lines)
    assert len(sections) == 1
    assert sections[0].title == "Lambda"
    assert any(child.title == "Concurrency" for child in sections[0].children)
