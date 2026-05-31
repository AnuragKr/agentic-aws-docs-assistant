from bs4 import BeautifulSoup

from domain.models import ParsedDocument, RawDocument
from ingestion.parsers.base import DocumentParser
from ingestion.parsers.hierarchy import extract_hierarchy_from_html

HTML_EXTENSIONS = {".html", ".htm"}


class HtmlParser(DocumentParser):
    def supports(self, extension: str) -> bool:
        return extension in HTML_EXTENSIONS

    def parse(self, document: RawDocument) -> ParsedDocument:
        html = document.content if isinstance(document.content, str) else document.content.decode(
            "utf-8", errors="replace"
        )
        soup = BeautifulSoup(html, "lxml")
        text = soup.get_text("\n\n", strip=True)
        sections = extract_hierarchy_from_html(soup)
        return ParsedDocument(
            key=document.key,
            text=text,
            extension=document.extension,
            etag=document.etag,
            last_modified=document.last_modified,
            sections=sections,
        )
