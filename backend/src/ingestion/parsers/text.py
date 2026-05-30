from domain.models import ParsedDocument, RawDocument
from ingestion.parsers.base import DocumentParser


class TextParser(DocumentParser):
    def supports(self, extension: str) -> bool:
        return extension == ".txt"

    def parse(self, document: RawDocument) -> ParsedDocument:
        text = document.content if isinstance(document.content, str) else document.content.decode(
            "utf-8", errors="replace"
        )
        return ParsedDocument(
            key=document.key,
            text=text,
            extension=document.extension,
            etag=document.etag,
            last_modified=document.last_modified,
        )
