from abc import ABC, abstractmethod

from domain.models import ParsedDocument, RawDocument


class DocumentParser(ABC):
    """Strategy: parse raw bytes/text into plain text."""

    @abstractmethod
    def supports(self, extension: str) -> bool:
        ...

    @abstractmethod
    def parse(self, document: RawDocument) -> ParsedDocument:
        ...
