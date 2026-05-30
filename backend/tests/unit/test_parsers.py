from datetime import datetime, timezone

from domain.models import RawDocument, SectionNode
from ingestion.parsers.factory import ParserFactory
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


def test_docling_hierarchy_builds_section_tree() -> None:
    from ingestion.parsers.hierarchy import extract_hierarchy_from_docling

    class FakeItem:
        def __init__(self, label: str, text: str, level: int = 1):
            self.label = label
            self.text = text
            self.level = level

    class FakeDoc:
        def iterate_items(self):
            yield FakeItem("section_header", "Lambda", 1), 1
            yield FakeItem("text", "Intro paragraph"), 1
            yield FakeItem("section_header", "Concurrency", 2), 2
            yield FakeItem("text", "Concurrency details"), 2

    sections = extract_hierarchy_from_docling(FakeDoc())
    assert len(sections) == 1
    assert sections[0].title == "Lambda"
    assert any(c.title == "Concurrency" for c in sections[0].children)
