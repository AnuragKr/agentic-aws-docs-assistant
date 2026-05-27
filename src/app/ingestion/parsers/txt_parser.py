from app.ingestion.parsers.base import BaseParser


class TxtParser(BaseParser):
    def __init__(self) -> None:
        super().__init__({".txt"})
