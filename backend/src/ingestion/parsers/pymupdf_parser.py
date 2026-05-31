import fitz

from config.logging import get_logger, log_memory
from domain.models import ParsedDocument, RawDocument
from ingestion.parsers.base import DocumentParser
from ingestion.parsers.hierarchy import extract_hierarchy_from_pdf_lines

logger = get_logger(__name__)

PDF_EXTENSIONS = {".pdf"}


class PyMuPDFParser(DocumentParser):
    """Extract plain text from PDF via PyMuPDF, then derive heading hierarchy from font sizes."""

    def supports(self, extension: str) -> bool:
        return extension in PDF_EXTENSIONS

    def parse(self, document: RawDocument) -> ParsedDocument:
        data = document.content if isinstance(document.content, bytes) else document.content.encode()

        logger.info("pdf_parse_start", key=document.key, size=len(data))
        log_memory("pdf_parse_memory_before", logger=logger, key=document.key)

        with fitz.open(stream=data, filetype="pdf") as pdf:
            page_texts: list[str] = []
            lines_with_size: list[tuple[str, float]] = []

            for page in pdf:
                page_lines: list[tuple[str, float]] = []
                for block in page.get_text("dict").get("blocks", []):
                    if block.get("type") != 0:
                        continue
                    for line in block.get("lines", []):
                        spans = line.get("spans", [])
                        if not spans:
                            continue
                        line_text = "".join(span["text"] for span in spans).strip()
                        if not line_text:
                            continue
                        line_size = max(span["size"] for span in spans)
                        page_lines.append((line_text, line_size))

                if page_lines:
                    page_texts.append("\n".join(text for text, _ in page_lines))
                    lines_with_size.extend(page_lines)

            text = "\n\n".join(page_texts)
            sections = extract_hierarchy_from_pdf_lines(lines_with_size)

        log_memory("pdf_parse_memory_after", logger=logger, key=document.key)
        logger.info(
            "pdf_parse_complete",
            key=document.key,
            pages=len(page_texts),
            text_len=len(text),
            sections=len(sections),
        )

        return ParsedDocument(
            key=document.key,
            text=text,
            extension=document.extension,
            etag=document.etag,
            last_modified=document.last_modified,
            sections=sections,
        )
