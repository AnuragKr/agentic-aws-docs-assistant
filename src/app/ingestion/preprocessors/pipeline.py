from app.ingestion.ports.preprocessor import IPreprocessor
from app.ingestion.domain.document import ParsedDocument, PreprocessedDocument
from app.ingestion.preprocessors import steps


class PreprocessorPipeline(IPreprocessor):
    def process(self, document: ParsedDocument) -> PreprocessedDocument:
        text, code_blocks = steps.mask_code_fences(document.text)
        text = steps.remove_nav_noise(text)
        text = steps.dedupe_lines(text)
        text = steps.normalize_whitespace(text)
        text = steps.unmask_code_fences(text, code_blocks)

        sections = steps.detect_sections(text)
        if not sections and document.extension in {".md", ".markdown"}:
            sections = steps.detect_sections(f"# Document\n\n{text}")

        return PreprocessedDocument(
            key=document.key,
            text=text,
            extension=document.extension,
            sections=sections,
        )
