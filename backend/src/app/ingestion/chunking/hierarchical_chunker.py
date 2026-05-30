import hashlib
import re

from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.core.config import Settings
from app.ingestion.ports.chunker import IChunker
from app.ingestion.domain.chunk import Chunk, ContentType
from app.ingestion.domain.document import DocumentMetadata, PreprocessedDocument, SectionNode

CODE_FENCE_PATTERN = re.compile(r"```")


class HierarchicalChunker(IChunker):
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.chunk_size,
            chunk_overlap=settings.chunk_overlap,
            separators=["\n### ", "\n## ", "\n\n", "\n", " "],
        )

    def chunk(
        self,
        document: PreprocessedDocument,
        metadata: DocumentMetadata,
    ) -> list[Chunk]:
        chunks: list[Chunk] = []
        parent_ids: dict[int, str] = {}

        if document.sections:
            for section in document.sections:
                self._chunk_section(
                    section,
                    document,
                    metadata,
                    chunks,
                    parent_ids,
                    hierarchy=[],
                )
        else:
            self._chunk_text(
                document.text,
                document=document,
                metadata=metadata,
                chunks=chunks,
                hierarchy=[],
                section=None,
                subsection=None,
                parent_chunk_id=None,
                chunk_level="content",
            )

        for i, chunk in enumerate(chunks):
            chunk.chunk_index = i
        return chunks

    def _chunk_section(
        self,
        section: SectionNode,
        document: PreprocessedDocument,
        metadata: DocumentMetadata,
        chunks: list[Chunk],
        parent_ids: dict[int, str],
        hierarchy: list[str],
    ) -> None:
        hierarchy = hierarchy + [section.title]
        level_name = self._level_name(len(hierarchy))
        parent_chunk_id = parent_ids.get(section.level - 1) if section.level > 1 else None

        section_chunks = self._chunk_text(
            section.content or document.text,
            document=document,
            metadata=metadata,
            chunks=[],
            hierarchy=hierarchy,
            section=hierarchy[1] if len(hierarchy) > 1 else hierarchy[0] if hierarchy else None,
            subsection=hierarchy[2] if len(hierarchy) > 2 else None,
            parent_chunk_id=parent_chunk_id,
            chunk_level=level_name,
        )

        if section_chunks:
            parent_ids[section.level] = section_chunks[0].chunk_id
        chunks.extend(section_chunks)

        for child in section.children:
            self._chunk_section(child, document, metadata, chunks, parent_ids, hierarchy)

    def _chunk_text(
        self,
        text: str,
        *,
        document: PreprocessedDocument,
        metadata: DocumentMetadata,
        chunks: list[Chunk],
        hierarchy: list[str],
        section: str | None,
        subsection: str | None,
        parent_chunk_id: str | None,
        chunk_level: str,
    ) -> list[Chunk]:
        if not text.strip():
            return chunks

        parts = self._splitter.split_text(text)
        service = metadata.service or (hierarchy[0] if hierarchy else None)

        for part in parts:
            chunk_id = self._make_chunk_id(document.key, hierarchy, len(chunks), part)
            chunks.append(
                Chunk(
                    chunk_id=chunk_id,
                    content=part,
                    service=service,
                    section=section,
                    subsection=subsection,
                    section_hierarchy=hierarchy,
                    document_name=metadata.document_name,
                    source_url=metadata.source_url,
                    document_type=metadata.document_type,
                    topics=list(metadata.topics),
                    chunk_summary=self._summary(part, hierarchy),
                    content_type=self._content_type(part, hierarchy),
                    parent_chunk_id=parent_chunk_id,
                    chunk_level=chunk_level,
                )
            )
        return chunks

    @staticmethod
    def _level_name(depth: int) -> str:
        return {1: "service", 2: "section", 3: "subsection"}.get(depth, "content")

    @staticmethod
    def _make_chunk_id(key: str, hierarchy: list[str], index: int, text: str) -> str:
        raw = f"{key}|{'/'.join(hierarchy)}|{index}|{text[:64]}"
        return hashlib.sha256(raw.encode()).hexdigest()

    @staticmethod
    def _summary(text: str, hierarchy: list[str]) -> str:
        prefix = " > ".join(hierarchy)
        lead = text.strip().replace("\n", " ")[:160]
        if prefix:
            return f"{prefix}: {lead}"[:200]
        return lead[:200]

    @staticmethod
    def _content_type(text: str, hierarchy: list[str]) -> ContentType:
        if CODE_FENCE_PATTERN.search(text):
            return "code"
        if hierarchy and hierarchy[-1].lower().startswith("example"):
            return "example"
        return "text"
