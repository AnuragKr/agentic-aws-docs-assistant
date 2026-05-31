import fitz

from config.logging import get_logger, log_memory
from domain.models import ParsedDocument, RawDocument
from ingestion.parsers.base import DocumentParser
from ingestion.parsers.pdf_structure import build_pdf_document_structure

logger = get_logger(__name__)

PDF_EXTENSIONS = {".pdf"}


class PyMuPDFParser(DocumentParser):
    """Extract PDF text and hierarchical structure via TOC + font/bold heuristics."""

    def supports(self, extension: str) -> bool:
        return extension in PDF_EXTENSIONS

    def parse(self, document: RawDocument) -> ParsedDocument:
        data = document.content if isinstance(document.content, bytes) else document.content.encode()

        logger.info("pdf_parse_start", key=document.key, size=len(data))
        log_memory("pdf_parse_memory_before", logger=logger, key=document.key)

        with fitz.open(stream=data, filetype="pdf") as pdf:
            sections, text, total_pages = build_pdf_document_structure(pdf)
            leaf_count = sum(1 for _ in _count_leaves(sections))

        log_memory("pdf_parse_memory_after", logger=logger, key=document.key)
        logger.info(
            "pdf_parse_complete",
            key=document.key,
            pages=total_pages,
            text_len=len(text),
            top_level_sections=len(sections),
            leaf_sections=leaf_count,
        )

        return ParsedDocument(
            key=document.key,
            text=text,
            extension=document.extension,
            etag=document.etag,
            last_modified=document.last_modified,
            sections=sections,
            total_pages=total_pages,
        )


def _count_leaves(sections):
    for section in sections:
        if section.children:
            yield from _count_leaves(section.children)
        else:
            yield section
