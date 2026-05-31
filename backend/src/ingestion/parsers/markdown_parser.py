from domain.models import ParsedDocument, RawDocument
from ingestion.parsers.base import DocumentParser
from ingestion.parsers.hierarchy import extract_hierarchy_from_text

MARKDOWN_EXTENSIONS = {".md", ".markdown"}


class MarkdownParser(DocumentParser):
    def supports(self, extension: str) -> bool:
        return extension in MARKDOWN_EXTENSIONS

    def parse(self, document: RawDocument) -> ParsedDocument:
        text = document.content if isinstance(document.content, str) else document.content.decode(
            "utf-8", errors="replace"
        )
        sections = extract_hierarchy_from_text(text)
        return ParsedDocument(
            key=document.key,
            text=text,
            extension=document.extension,
            etag=document.etag,
            last_modified=document.last_modified,
            sections=sections,
        )
