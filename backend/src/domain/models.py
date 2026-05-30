from datetime import datetime
from enum import StrEnum
from uuid import uuid4

from pydantic import BaseModel, Field


class JobStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class RegistryStatus(StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


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


class SectionNode(BaseModel):
    title: str
    level: int
    content: str = ""
    children: list["SectionNode"] = Field(default_factory=list)


class PreprocessedDocument(BaseModel):
    key: str
    text: str
    extension: str
    etag: str
    last_modified: datetime
    sections: list[SectionNode] = Field(default_factory=list)


class DocumentMetadata(BaseModel):
    """Document-level metadata for Agentic RAG."""

    document_id: str
    title: str
    service: str | None = None
    service_category: str | None = None
    source_url: str
    document_type: str | None = None
    source_key: str
    last_modified: datetime
    etag: str
    document_summary: str = ""
    sections: list[SectionNode] = Field(default_factory=list)


class ChunkRecord(BaseModel):
    """Chunk with rich metadata for retrieval and filtering."""

    chunk_id: str
    document_id: str
    content: str
    service: str | None = None
    service_category: str | None = None
    title: str = ""
    section: str | None = None
    subsection: str | None = None
    source_url: str = ""
    document_type: str | None = None
    chunk_summary: str = ""
    keywords: list[str] = Field(default_factory=list)
    topics: list[str] = Field(default_factory=list)
    chunk_index: int = 0
    total_chunks: int = 0
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
    processed_at: str | None = None
    error_message: str | None = None


class IngestionJob(BaseModel):
    job_id: str = Field(default_factory=lambda: str(uuid4()))
    status: JobStatus = JobStatus.PENDING
    phase: str | None = None
    documents_processed: int = 0
    documents_skipped: int = 0
    documents_failed: int = 0
    chunks_written: int = 0
    embeddings_generated: int = 0
    errors: list[str] = Field(default_factory=list)
    prefix: str | None = None
    max_documents: int | None = None
    force_reprocess: bool = False
    started_at: datetime = Field(default_factory=datetime.utcnow)
    finished_at: datetime | None = None


# Interview-friendly aliases
Document = DocumentMetadata
Chunk = ChunkRecord
ProcessingRecord = DocumentRegistryEntry
