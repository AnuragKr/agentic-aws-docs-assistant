from bs4 import BeautifulSoup

from app.ingestion.parsers.base import BaseParser
from app.ingestion.domain.document import ParsedDocument, RawDocument


class HtmlParser(BaseParser):
    def __init__(self) -> None:
        super().__init__({".html", ".htm"})

    def parse(self, document: RawDocument) -> ParsedDocument:
        soup = BeautifulSoup(document.content, "lxml")
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()
        text = soup.get_text(separator="\n")
        lines = [line.strip() for line in text.splitlines()]
        cleaned = "\n".join(line for line in lines if line)
        return ParsedDocument(
            key=document.key,
            text=cleaned,
            extension=document.extension,
        )
