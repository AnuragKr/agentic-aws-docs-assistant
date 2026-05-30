import hashlib
import re

from langchain_text_splitters import RecursiveCharacterTextSplitter

from config.logging import get_logger
from config.settings import Settings
from config.token_utils import count_tokens, get_token_encoder
from domain.models import ChunkRecord, DocumentMetadata, PreprocessedDocument, SectionNode

logger = get_logger(__name__)

CODE_FENCE_RE = re.compile(r"```")


class HierarchicalChunker:
    """
    Custom hierarchical chunker (Strategy pattern).

    Heading → Subheading → semantic paragraph groups.
    LangChain splitter used ONLY as fallback when a section exceeds token limit.
    """

    def __init__(self, settings: Settings) -> None:
        self._max_tokens = settings.chunk_max_tokens
        self._overlap_tokens = settings.chunk_overlap_tokens
        self._encoder = get_token_encoder()
        self._fallback_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self._max_tokens,
            chunk_overlap=self._overlap_tokens,
            length_function=lambda t: count_tokens(t, self._encoder),
        )

    def chunk(
        self,
        document: PreprocessedDocument,
        metadata: DocumentMetadata,
    ) -> list[ChunkRecord]:
        chunks: list[ChunkRecord] = []
        if document.sections:
            for section in document.sections:
                self._chunk_section(section, document, metadata, chunks, hierarchy=[])
        else:
            self._chunk_text(
                document.text,
                document=document,
                metadata=metadata,
                chunks=chunks,
                section=None,
                subsection=None,
                heading_level=None,
            )
        logger.info("chunks_created", source_key=document.key, count=len(chunks))
        return chunks

    def _chunk_section(
        self,
        section: SectionNode,
        document: PreprocessedDocument,
        metadata: DocumentMetadata,
        chunks: list[ChunkRecord],
        hierarchy: list[tuple[str, int]],
    ) -> None:
        hierarchy = hierarchy + [(section.title, section.level)]
        section_name = hierarchy[1][0] if len(hierarchy) > 1 else hierarchy[0][0]
        subsection = hierarchy[2][0] if len(hierarchy) > 2 else None
        self._chunk_text(
            section.content or document.text,
            document=document,
            metadata=metadata,
            chunks=chunks,
            section=section_name,
            subsection=subsection,
            heading_level=section.level,
        )
        for child in section.children:
            self._chunk_section(child, document, metadata, chunks, hierarchy)

    def _chunk_text(
        self,
        text: str,
        *,
        document: PreprocessedDocument,
        metadata: DocumentMetadata,
        chunks: list[ChunkRecord],
        section: str | None,
        subsection: str | None,
        heading_level: int | None,
    ) -> None:
        if not text.strip():
            return

        for part in self._split_by_paragraphs(text):
            chunk_id = self._chunk_id(document.key, len(chunks), part)
            chunks.append(
                ChunkRecord(
                    chunk_id=chunk_id,
                    document_id=metadata.document_id,
                    content=part,
                    service=metadata.service,
                    service_category=metadata.service_category,
                    title=metadata.title,
                    section=section,
                    subsection=subsection,
                    source_url=metadata.source_url,
                    content_type="code" if CODE_FENCE_RE.search(part) else "text",
                    chunk_level="semantic",
                    heading_level=heading_level,
                )
            )

    def _split_by_paragraphs(self, text: str) -> list[str]:
        """Group paragraphs semantically; fallback to LangChain only if too large."""
        parts: list[str] = []
        paragraphs = [p.strip() for p in re.split(r"\n\n+", text) if p.strip()]
        buffer = ""

        for para in paragraphs:
            candidate = f"{buffer}\n\n{para}".strip() if buffer else para
            if count_tokens(candidate, self._encoder) <= self._max_tokens:
                buffer = candidate
            else:
                if buffer:
                    parts.extend(self._maybe_fallback_split(buffer))
                buffer = para

        if buffer:
            parts.extend(self._maybe_fallback_split(buffer))
        return parts

    def _maybe_fallback_split(self, text: str) -> list[str]:
        if count_tokens(text, self._encoder) <= self._max_tokens:
            return [text]
        logger.info("chunk_fallback_langchain", tokens=count_tokens(text, self._encoder))
        return self._fallback_splitter.split_text(text)

    @staticmethod
    def _chunk_id(key: str, index: int, text: str) -> str:
        raw = f"{key}|{index}|{text[:64]}"
        return hashlib.sha256(raw.encode()).hexdigest()
