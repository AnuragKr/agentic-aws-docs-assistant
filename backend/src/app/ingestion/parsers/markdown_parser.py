from app.ingestion.parsers.base import BaseParser
from app.ingestion.domain.document import ParsedDocument, RawDocument


class MarkdownParser(BaseParser):
    def __init__(self) -> None:
        super().__init__({".md", ".markdown"})

    def parse(self, document: RawDocument) -> ParsedDocument:
        # Preserve markdown structure for downstream section detection.
        return ParsedDocument(
            key=document.key,
            text=document.content.strip(),
            extension=document.extension,
        )
