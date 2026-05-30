from app.ingestion.ports.parser import IDocumentParser
from app.ingestion.domain.document import ParsedDocument, RawDocument


class BaseParser(IDocumentParser):
    def __init__(self, extensions: set[str]) -> None:
        self._extensions = extensions

    def supports(self, extension: str) -> bool:
        return extension.lower() in self._extensions

    def parse(self, document: RawDocument) -> ParsedDocument:
        return ParsedDocument(
            key=document.key,
            text=document.content,
            extension=document.extension,
        )
