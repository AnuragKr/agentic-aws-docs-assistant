import hashlib
import re

from config.logging import get_logger
from config.settings import Settings
from config.token_utils import count_tokens, get_token_encoder
from domain.exceptions import ChunkExplosionError
from domain.models import ChunkRecord, DocumentMetadata, PreprocessedDocument, SectionNode
from ingestion.chunkers.sentence_splitter import build_sentence_chunks
from ingestion.parsers.best_practices import path_label

logger = get_logger(__name__)

CODE_FENCE_RE = re.compile(r"```")


class HierarchicalChunker:
    """
    Section-first chunker that never splits mid-sentence.

    Accumulates complete sentences within each TOC leaf section toward
    800-token targets (500–1200 bounds) with sentence-aligned overlap.
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._min_tokens = settings.chunk_min_tokens
        self._max_tokens = settings.chunk_max_tokens
        self._target_tokens = settings.chunk_target_tokens
        self._overlap_tokens = settings.chunk_overlap_tokens
        self._max_chunks = settings.chunk_max_chunks_per_document
        self._encoder = get_token_encoder()

    def chunk(
        self,
        document: PreprocessedDocument,
        metadata: DocumentMetadata,
    ) -> list[ChunkRecord]:
        chunks: list[ChunkRecord] = []
        if document.sections:
            for section in document.sections:
                self._chunk_section(section, document, metadata, chunks, ancestors=[])
        else:
            self._chunk_text(
                document.text,
                document=document,
                metadata=metadata,
                chunks=chunks,
                section=None,
                ancestors=[],
            )

        merged = self._merge_adjacent_small(chunks, document)
        total = len(merged)
        for index, chunk in enumerate(merged):
            chunk.chunk_index = index
            chunk.chunk_order = index
            chunk.total_chunks = total

        if total > self._max_chunks:
            logger.error(
                "chunk_explosion",
                source_key=document.key,
                chunk_count=total,
                limit=self._max_chunks,
            )
            raise ChunkExplosionError(total, self._max_chunks, document.key)

        self._log_chunk_token_stats(document.key, merged)
        return merged

    def _log_chunk_token_stats(self, source_key: str, chunks: list[ChunkRecord]) -> None:
        token_counts = [count_tokens(chunk.content, self._encoder) for chunk in chunks]
        logger.info(
            "chunks_created",
            source_key=source_key,
            chunk_count=len(chunks),
            avg_chunk_tokens=round(sum(token_counts) / len(token_counts), 1) if token_counts else 0,
            min_chunk_tokens=min(token_counts) if token_counts else 0,
            max_chunk_tokens=max(token_counts) if token_counts else 0,
            target_tokens=self._target_tokens,
            configured_min_tokens=self._min_tokens,
            configured_max_tokens=self._max_tokens,
        )

    @staticmethod
    def iter_leaves(sections: list[SectionNode]):
        for section in sections:
            if section.children:
                yield from HierarchicalChunker.iter_leaves(section.children)
            else:
                yield section

    def _chunk_section(
        self,
        section: SectionNode,
        document: PreprocessedDocument,
        metadata: DocumentMetadata,
        chunks: list[ChunkRecord],
        ancestors: list[SectionNode],
    ) -> None:
        chain = ancestors + [section]
        if section.children:
            for child in section.children:
                self._chunk_section(child, document, metadata, chunks, chain)
            return

        text = section.content.strip()
        if not text:
            return

        self._chunk_text(
            text,
            document=document,
            metadata=metadata,
            chunks=chunks,
            section=section,
            ancestors=chain,
        )

    def _chunk_text(
        self,
        text: str,
        *,
        document: PreprocessedDocument,
        metadata: DocumentMetadata,
        chunks: list[ChunkRecord],
        section: SectionNode | None,
        ancestors: list[SectionNode],
    ) -> None:
        if not text.strip():
            return

        hierarchy_path = [path_label(node.title, node.best_practice_id) for node in ancestors]
        if section and not ancestors:
            hierarchy_path = [path_label(section.title, section.best_practice_id)]

        chapter = section.chapter if section and section.chapter else _label_from_path(hierarchy_path, 0)
        section_name = (
            section.section if section and section.section else _label_from_path(hierarchy_path, 1)
        )
        subsection = (
            section.subsection if section and section.subsection else _label_from_path(hierarchy_path, 2)
        )
        best_practice_id = section.best_practice_id if section else None
        best_practice_title = section.best_practice_title if section else None
        page_number = section.page_start if section else None
        heading_level = section.level if section else None

        for part in self._split_text(text):
            if len(chunks) >= self._max_chunks:
                raise ChunkExplosionError(len(chunks) + 1, self._max_chunks, document.key)

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
                    document_title=metadata.document_title or metadata.title,
                    chapter=chapter,
                    section=section_name,
                    subsection=subsection,
                    best_practice_id=best_practice_id,
                    best_practice_title=best_practice_title,
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

    def _split_text(self, text: str) -> list[str]:
        return build_sentence_chunks(
            text,
            target_tokens=self._target_tokens,
            min_tokens=self._min_tokens,
            max_tokens=self._max_tokens,
            overlap_tokens=self._overlap_tokens,
            encoder=self._encoder,
        )

    def _merge_adjacent_small(
        self,
        chunks: list[ChunkRecord],
        document: PreprocessedDocument,
    ) -> list[ChunkRecord]:
        """Merge undersized chunks in the same section when they fit within max_tokens."""
        if len(chunks) <= 1:
            return chunks

        merged: list[ChunkRecord] = []
        for chunk in chunks:
            if merged and self._try_merge_into_previous(merged, chunk, document.key):
                continue
            merged.append(chunk)

        while len(merged) >= 2 and self._should_merge_trailing(merged[-1], merged[-2]):
            tail = merged.pop()
            if not self._try_merge_into_previous(merged, tail, document.key):
                merged.append(tail)
                break

        return merged

    def _should_merge_trailing(self, chunk: ChunkRecord, previous: ChunkRecord) -> bool:
        if chunk.hierarchy_path != previous.hierarchy_path:
            return False
        chunk_tokens = count_tokens(chunk.content, self._encoder)
        if chunk_tokens >= self._min_tokens:
            return False
        combined = f"{previous.content} {chunk.content}".strip()
        return count_tokens(combined, self._encoder) <= self._max_tokens

    def _try_merge_into_previous(
        self,
        merged: list[ChunkRecord],
        chunk: ChunkRecord,
        document_key: str,
    ) -> bool:
        if not merged or merged[-1].hierarchy_path != chunk.hierarchy_path:
            return False

        previous = merged[-1]
        previous_tokens = count_tokens(previous.content, self._encoder)
        chunk_tokens = count_tokens(chunk.content, self._encoder)
        if chunk_tokens >= self._min_tokens and previous_tokens >= self._min_tokens:
            return False

        combined = f"{previous.content} {chunk.content}".strip()
        if count_tokens(combined, self._encoder) > self._max_tokens:
            return False

        merged[-1] = previous.model_copy(
            update={
                "content": combined,
                "chunk_id": self._chunk_id(document_key, len(merged) - 1, combined),
                "content_type": (
                    "code" if CODE_FENCE_RE.search(combined) else previous.content_type
                ),
            }
        )
        return True

    @staticmethod
    def _chunk_id(key: str, index: int, text: str) -> str:
        raw = f"{key}|{index}|{text[:64]}"
        return hashlib.sha256(raw.encode()).hexdigest()


def _label_from_path(hierarchy_path: list[str], index: int) -> str | None:
    if index < len(hierarchy_path):
        return hierarchy_path[index]
    return None
