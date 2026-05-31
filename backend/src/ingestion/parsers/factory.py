from config.logging import UnsupportedFormatError
from domain.models import ParsedDocument, RawDocument
from ingestion.parsers.base import DocumentParser
from ingestion.parsers.html_parser import HtmlParser
from ingestion.parsers.markdown_parser import MarkdownParser
from ingestion.parsers.pymupdf_parser import PyMuPDFParser
from ingestion.parsers.text import TextParser


class ParserFactory:
    """Factory: PyMuPDF for PDF, lightweight parsers for HTML/MD/TXT."""

    def __init__(self, parsers: list[DocumentParser] | None = None) -> None:
        self._parsers = parsers or [
            PyMuPDFParser(),
            HtmlParser(),
            MarkdownParser(),
            TextParser(),
        ]

    def parse(self, document: RawDocument) -> ParsedDocument:
        for parser in self._parsers:
            if parser.supports(document.extension):
                return parser.parse(document)
        raise UnsupportedFormatError(f"No parser for {document.extension}")
