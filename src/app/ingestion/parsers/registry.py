from app.core.exceptions import UnsupportedFormatError
from app.ingestion.ports.parser import IDocumentParser
from app.ingestion.domain.document import ParsedDocument, RawDocument
from app.ingestion.parsers.html_parser import HtmlParser
from app.ingestion.parsers.markdown_parser import MarkdownParser
from app.ingestion.parsers.txt_parser import TxtParser


class ParserRegistry:
    def __init__(self, parsers: list[IDocumentParser] | None = None) -> None:
        self._parsers = parsers or [TxtParser(), MarkdownParser(), HtmlParser()]

    def parse(self, document: RawDocument) -> ParsedDocument:
        for parser in self._parsers:
            if parser.supports(document.extension):
                return parser.parse(document)
        raise UnsupportedFormatError(f"No parser for extension {document.extension}")
