import tempfile
from pathlib import Path

from config.logging import get_logger
from domain.models import ParsedDocument, RawDocument
from ingestion.parsers.base import DocumentParser
from ingestion.parsers.hierarchy import extract_hierarchy_from_docling

logger = get_logger(__name__)

DOCLING_EXTENSIONS = {".pdf", ".html", ".htm", ".md", ".markdown"}


class DoclingParser(DocumentParser):
    """Primary parser: PDF, HTML, Markdown via Docling (CPU-friendly, no OCR)."""

    def __init__(self) -> None:
        from docling.datamodel.accelerator_options import AcceleratorDevice, AcceleratorOptions
        from docling.datamodel.base_models import InputFormat
        from docling.datamodel.pipeline_options import PdfPipelineOptions
        from docling.document_converter import DocumentConverter, PdfFormatOption

        pdf_options = PdfPipelineOptions()
        pdf_options.do_ocr = False
        pdf_options.do_table_structure = False
        pdf_options.force_backend_text = True
        pdf_options.generate_page_images = False
        pdf_options.generate_picture_images = False
        pdf_options.accelerator_options = AcceleratorOptions(
            num_threads=1,
            device=AcceleratorDevice.CPU,
        )
        pdf_options.layout_batch_size = 1
        pdf_options.table_batch_size = 1

        self._converter = DocumentConverter(
            format_options={
                InputFormat.PDF: PdfFormatOption(pipeline_options=pdf_options),
            }
        )
        logger.info("docling_parser_ready", do_ocr=False, device="cpu")

    def supports(self, extension: str) -> bool:
        return extension in DOCLING_EXTENSIONS

    def parse(self, document: RawDocument) -> ParsedDocument:
        suffix = document.extension if document.extension.startswith(".") else f".{document.extension}"
        data = document.content if isinstance(document.content, bytes) else document.content.encode()

        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(data)
            tmp_path = Path(tmp.name)

        try:
            logger.info("docling_parse_start", key=document.key, size=len(data))
            result = self._converter.convert(str(tmp_path))
            doc = result.document
            markdown = doc.export_to_markdown()
            sections = extract_hierarchy_from_docling(doc)
            logger.info(
                "docling_parse_complete",
                key=document.key,
                text_len=len(markdown),
                sections=len(sections),
            )

            return ParsedDocument(
                key=document.key,
                text=markdown,
                extension=document.extension,
                etag=document.etag,
                last_modified=document.last_modified,
                sections=sections,
            )
        finally:
            tmp_path.unlink(missing_ok=True)
