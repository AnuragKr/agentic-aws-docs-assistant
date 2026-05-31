from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class RegistryStatus(StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    STORED = "stored"
    INDEXED = "indexed"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"

    @classmethod
    def fully_processed(cls) -> frozenset["RegistryStatus"]:
        """Statuses that mean ingestion finished successfully."""
        return frozenset({cls.INDEXED, cls.COMPLETED})


class IngestionRun(BaseModel):
    """Options and metrics for a single ingestion run (CLI or API)."""

    max_documents: int | None = None
    force_reprocess: bool = False
    phase: str | None = None
    documents_processed: int = 0
    documents_skipped: int = 0
    documents_failed: int = 0
    chunks_written: int = 0
    embeddings_generated: int = 0
    errors: list[str] = Field(default_factory=list)


class SourceObject(BaseModel):
    key: str
    etag: str
    last_modified: datetime
    size: int = 0


class RawDocument(BaseModel):
    key: str
    content: bytes | str
    extension: str
    etag: str
    last_modified: datetime


class ParsedDocument(BaseModel):
    key: str
    text: str
    extension: str
    etag: str
    last_modified: datetime
    sections: list["SectionNode"] = Field(default_factory=list)
    total_pages: int = 0
    document_title: str = ""


class SectionNode(BaseModel):
    title: str
    level: int
    content: str = ""
    page_start: int | None = None
    page_end: int | None = None
    chapter: str | None = None
    section: str | None = None
    subsection: str | None = None
    best_practice_id: str | None = None
    best_practice_title: str | None = None
    children: list["SectionNode"] = Field(default_factory=list)


class PreprocessedDocument(BaseModel):
    key: str
    text: str
    extension: str
    etag: str
    last_modified: datetime
    sections: list[SectionNode] = Field(default_factory=list)
    total_pages: int = 0
    document_title: str = ""


class DocumentMetadata(BaseModel):
    """Document-level metadata for Agentic RAG."""

    document_id: str
    title: str
    document_title: str = ""
    service: str | None = None
    service_category: str | None = None
    services: list[str] = Field(default_factory=list)
    source_url: str
    source_file: str = ""
    document_type: str | None = None
    source_key: str
    last_modified: datetime
    etag: str
    document_summary: str = ""
    total_pages: int = 0
    sections: list[SectionNode] = Field(default_factory=list)


class ChunkRecord(BaseModel):
    """Chunk with rich metadata for retrieval and filtering."""

    chunk_id: str
    document_id: str
    content: str
    service: str | None = None
    service_category: str | None = None
    services: list[str] = Field(default_factory=list)
    title: str = ""
    document_title: str = ""
    chapter: str | None = None
    section: str | None = None
    subsection: str | None = None
    best_practice_id: str | None = None
    best_practice_title: str | None = None
    hierarchy_path: list[str] = Field(default_factory=list)
    source_url: str = ""
    source_file: str = ""
    document_type: str | None = None
    chunk_summary: str = ""
    keywords: list[str] = Field(default_factory=list)
    topics: list[str] = Field(default_factory=list)
    chunk_index: int = 0
    chunk_order: int = 0
    total_chunks: int = 0
    page_number: int | None = None
    total_pages: int = 0
    prev_chunk_id: str | None = None
    next_chunk_id: str | None = None
    content_type: str = "text"
    chunk_level: str = "semantic"
    heading_level: int | None = None
    embedding: list[float] = Field(default_factory=list)


class DocumentRegistryEntry(BaseModel):
    """DynamoDB processing registry record."""

    document_id: str
    source_key: str
    etag: str
    last_modified: str
    status: RegistryStatus
    document_hash: str | None = None
    processed_at: str | None = None
    indexed_at: str | None = None
    chunk_count: int = 0
    embedding_count: int = 0
    error_message: str | None = None


class RetrievedChunk(BaseModel):
    """Search result returned to API clients."""

    chunk_id: str
    document_id: str
    content: str
    score: float
    service: str | None = None
    service_category: str | None = None
    title: str = ""
    document_title: str = ""
    source_file: str = ""
    section: str | None = None
    subsection: str | None = None
    page_number: int | None = None
    source_url: str = ""
    chunk_summary: str = ""
    keywords: list[str] = Field(default_factory=list)
    topics: list[str] = Field(default_factory=list)
    citation: str = ""


# Interview-friendly aliases
Document = DocumentMetadata
Chunk = ChunkRecord
ProcessingRecord = DocumentRegistryEntry
