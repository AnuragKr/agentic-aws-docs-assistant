from functools import lru_cache

from config.logging import UnsupportedFormatError
from domain.models import ParsedDocument, RawDocument
from ingestion.parsers.base import DocumentParser
from ingestion.parsers.docling_parser import DoclingParser
from ingestion.parsers.text import TextParser


@lru_cache(maxsize=1)
def _shared_docling_parser() -> DoclingParser:
    """Load Docling models once per process."""
    return DoclingParser()


class ParserFactory:
    """Factory: Docling for PDF/HTML/MD, plain text parser for .txt."""

    def __init__(self, parsers: list[DocumentParser] | None = None) -> None:
        self._parsers = parsers or [_shared_docling_parser(), TextParser()]

    def parse(self, document: RawDocument) -> ParsedDocument:
        for parser in self._parsers:
            if parser.supports(document.extension):
                return parser.parse(document)
        raise UnsupportedFormatError(f"No parser for {document.extension}")
