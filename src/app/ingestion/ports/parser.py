from abc import ABC, abstractmethod

from app.ingestion.domain.document import ParsedDocument, RawDocument


class IDocumentParser(ABC):
    @abstractmethod
    def parse(self, document: RawDocument) -> ParsedDocument:
        pass

    @abstractmethod
    def supports(self, extension: str) -> bool:
        pass
