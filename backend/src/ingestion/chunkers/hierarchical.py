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

    Heading → Subheading → semantic paragraph groups (leaf sections only).
    Targets 800–1200 tokens with 10–20% overlap; LangChain fallback for oversized text.
    """

    def __init__(self, settings: Settings) -> None:
        self._min_tokens = settings.chunk_min_tokens
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
                self._chunk_section(section, document, metadata, chunks, hierarchy_path=[])
        else:
            self._chunk_text(
                document.text,
                document=document,
                metadata=metadata,
                chunks=chunks,
                hierarchy_path=[],
                heading_level=None,
                page_number=None,
            )

        merged = self._merge_small_chunks(chunks, document, metadata)
        total = len(merged)
        for index, chunk in enumerate(merged):
            chunk.chunk_index = index
            chunk.chunk_order = index
            chunk.total_chunks = total

        logger.info(
            "chunks_created",
            source_key=document.key,
            count=total,
            min_tokens=self._min_tokens,
            max_tokens=self._max_tokens,
        )
        return merged

    def _chunk_section(
        self,
        section: SectionNode,
        document: PreprocessedDocument,
        metadata: DocumentMetadata,
        chunks: list[ChunkRecord],
        hierarchy_path: list[str],
    ) -> None:
        path = hierarchy_path + [section.title]

        if section.children:
            for child in section.children:
                self._chunk_section(child, document, metadata, chunks, path)
            return

        text = section.content.strip()
        if not text:
            return

        self._chunk_text(
            text,
            document=document,
            metadata=metadata,
            chunks=chunks,
            hierarchy_path=path,
            heading_level=section.level,
            page_number=section.page_start,
        )

    def _chunk_text(
        self,
        text: str,
        *,
        document: PreprocessedDocument,
        metadata: DocumentMetadata,
        chunks: list[ChunkRecord],
        hierarchy_path: list[str],
        heading_level: int | None,
        page_number: int | None,
    ) -> None:
        if not text.strip():
            return

        section, subsection = _section_labels(hierarchy_path)

        for part in self._split_by_paragraphs(text):
            chunk_id = self._chunk_id(document.key, len(chunks), part)
            chunks.append(
                ChunkRecord(
                    chunk_id=chunk_id,
                    document_id=metadata.document_id,
                    content=part,
                    service=metadata.service,
                    service_category=metadata.service_category,
                    services=list(metadata.services),
                    title=metadata.title,
                    section=section,
                    subsection=subsection,
                    hierarchy_path=list(hierarchy_path),
                    source_url=metadata.source_url,
                    source_file=metadata.source_file,
                    document_type=metadata.document_type,
                    page_number=page_number,
                    total_pages=metadata.total_pages,
                    content_type="code" if CODE_FENCE_RE.search(part) else "text",
                    chunk_level="semantic",
                    heading_level=heading_level,
                )
            )

    def _split_by_paragraphs(self, text: str) -> list[str]:
        """Group paragraphs toward min/max token targets; fallback split if oversized."""
        parts: list[str] = []
        paragraphs = [p.strip() for p in re.split(r"\n\n+", text) if p.strip()]
        buffer = ""

        for para in paragraphs:
            candidate = f"{buffer}\n\n{para}".strip() if buffer else para
            token_count = count_tokens(candidate, self._encoder)

            if token_count <= self._max_tokens:
                buffer = candidate
                continue

            if buffer:
                parts.extend(self._emit_parts(buffer))
                buffer = ""

            if count_tokens(para, self._encoder) <= self._max_tokens:
                buffer = para
            else:
                parts.extend(self._maybe_fallback_split(para))

        if buffer:
            parts.extend(self._emit_parts(buffer))
        return parts

    def _emit_parts(self, text: str) -> list[str]:
        tokens = count_tokens(text, self._encoder)
        if tokens <= self._max_tokens:
            return [text]
        return self._maybe_fallback_split(text)

    def _merge_small_chunks(
        self,
        chunks: list[ChunkRecord],
        document: PreprocessedDocument,
        metadata: DocumentMetadata,
    ) -> list[ChunkRecord]:
        if len(chunks) <= 1:
            return chunks

        merged: list[ChunkRecord] = []
        for chunk in chunks:
            chunk_tokens = count_tokens(chunk.content, self._encoder)
            if (
                merged
                and chunk_tokens < self._min_tokens
                and count_tokens(merged[-1].content, self._encoder) < self._min_tokens
                and merged[-1].hierarchy_path == chunk.hierarchy_path
            ):
                combined = f"{merged[-1].content}\n\n{chunk.content}"
                if count_tokens(combined, self._encoder) <= self._max_tokens:
                    prev = merged[-1]
                    merged[-1] = prev.model_copy(
                        update={
                            "content": combined,
                            "chunk_id": self._chunk_id(
                                document.key,
                                len(merged) - 1,
                                combined,
                            ),
                            "content_type": (
                                "code"
                                if CODE_FENCE_RE.search(combined)
                                else prev.content_type
                            ),
                        }
                    )
                    continue
            merged.append(chunk)

        return merged

    def _maybe_fallback_split(self, text: str) -> list[str]:
        if count_tokens(text, self._encoder) <= self._max_tokens:
            return [text]
        logger.info("chunk_fallback_langchain", tokens=count_tokens(text, self._encoder))
        return self._fallback_splitter.split_text(text)

    @staticmethod
    def _chunk_id(key: str, index: int, text: str) -> str:
        raw = f"{key}|{index}|{text[:64]}"
        return hashlib.sha256(raw.encode()).hexdigest()


def _section_labels(hierarchy_path: list[str]) -> tuple[str | None, str | None]:
    if not hierarchy_path:
        return None, None
    if len(hierarchy_path) == 1:
        return hierarchy_path[0], None
    subsection = hierarchy_path[2] if len(hierarchy_path) > 2 else None
    return hierarchy_path[1], subsection
