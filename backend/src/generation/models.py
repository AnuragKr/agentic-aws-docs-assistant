from pydantic import BaseModel, Field

from domain.models import RetrievedChunk


class SourceReference(BaseModel):
    document_name: str
    page_number: int | None = None
    section_title: str | None = None


class GenerationRequest(BaseModel):
    question: str
    retrieved_chunks: list[RetrievedChunk] = Field(default_factory=list)


class GenerationResponse(BaseModel):
    answer: str
    sources: list[SourceReference] = Field(default_factory=list)
    model_id: str
    latency_ms: float
