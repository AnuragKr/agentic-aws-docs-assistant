import fitz

from config.logging import get_logger, log_memory
from domain.models import ParsedDocument, RawDocument
from ingestion.parsers.base import DocumentParser
from ingestion.parsers.pdf_structure import build_pdf_document_structure

logger = get_logger(__name__)

PDF_EXTENSIONS = {".pdf"}


class PyMuPDFParser(DocumentParser):
    """Extract PDF text and hierarchical structure via TOC with font fallback."""

    def supports(self, extension: str) -> bool:
        return extension in PDF_EXTENSIONS

    def parse(self, document: RawDocument) -> ParsedDocument:
        data = document.content if isinstance(document.content, bytes) else document.content.encode()

        logger.info("pdf_parse_start", key=document.key, size=len(data))
        log_memory("pdf_parse_memory_before", logger=logger, key=document.key)

        with fitz.open(stream=data, filetype="pdf") as pdf:
            structure = build_pdf_document_structure(pdf)
            leaf_count = sum(1 for _ in _count_leaves(structure.sections))

        log_memory("pdf_parse_memory_after", logger=logger, key=document.key)
        logger.info(
            "pdf_parse_complete",
            key=document.key,
            pages=structure.total_pages,
            document_title=structure.document_title,
            text_len=len(structure.text),
            top_level_sections=len(structure.sections),
            leaf_sections=leaf_count,
            section_count=structure.section_count,
        )

        return ParsedDocument(
            key=document.key,
            text=structure.text,
            extension=document.extension,
            etag=document.etag,
            last_modified=document.last_modified,
            sections=structure.sections,
            total_pages=structure.total_pages,
            document_title=structure.document_title,
        )


def _count_leaves(sections):
    for section in sections:
        if section.children:
            yield from _count_leaves(section.children)
        else:
            yield section
