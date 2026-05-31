from config.utils import normalize_unicode
from domain.models import ParsedDocument, PreprocessedDocument
from ingestion.preprocessors import steps


class DocumentPreprocessor:
    """Lightweight cleanup — heading hierarchy comes from parsers."""

    def process(self, document: ParsedDocument) -> PreprocessedDocument:
        text = document.text
        text = steps.remove_navigation(text)
        text = steps.remove_headers_footers(text)
        text = normalize_unicode(text)
        text = steps.normalize_whitespace(text)
        text = steps.preserve_links(text)

        return PreprocessedDocument(
            key=document.key,
            text=text,
            extension=document.extension,
            etag=document.etag,
            last_modified=document.last_modified,
            sections=document.sections,
            total_pages=document.total_pages,
        )
