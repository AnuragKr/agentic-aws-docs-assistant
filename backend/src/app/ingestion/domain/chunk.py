from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

ContentType = Literal["text", "code", "example"]


class Chunk(BaseModel):
    chunk_id: str
    content: str
    service: str | None = None
    section: str | None = None
    subsection: str | None = None
    section_hierarchy: list[str] = Field(default_factory=list)
    document_name: str = ""
    source_url: str = ""
    chunk_index: int = 0
    document_type: str | None = None
    keywords: list[str] = Field(default_factory=list)
    topics: list[str] = Field(default_factory=list)
    chunk_summary: str = ""
    content_type: ContentType = "text"
    parent_chunk_id: str | None = None
    chunk_level: str = "content"
    ingestion_timestamp: datetime | None = None
