from abc import ABC, abstractmethod

from app.ingestion.domain.document import ParsedDocument, PreprocessedDocument


class IPreprocessor(ABC):
    @abstractmethod
    def process(self, document: ParsedDocument) -> PreprocessedDocument:
        pass
