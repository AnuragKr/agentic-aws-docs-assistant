from pydantic import BaseModel, Field

from domain.intent import QueryIntent
from domain.models import RetrievedChunk


class SourceReference(BaseModel):
    document_name: str
    page_number: int | None = None
    section_title: str | None = None


class ExternalSearchResult(BaseModel):
    title: str
    url: str
    content: str


class GenerationRequest(BaseModel):
    question: str
    retrieved_chunks: list[RetrievedChunk] = Field(default_factory=list)
    external_results: list[ExternalSearchResult] = Field(default_factory=list)
    intent: QueryIntent = QueryIntent.EXPLAIN


class GenerationResponse(BaseModel):
    answer: str
    sources: list[SourceReference] = Field(default_factory=list)
    model_id: str
    latency_ms: float


INSUFFICIENT_EVIDENCE_MESSAGE = (
    "I could not find enough information in the AWS knowledge base to answer this question reliably."
)

DOMAIN_REJECTION_MESSAGE = (
    "This assistant is specialized for AWS-related questions and cannot answer "
    "questions outside the AWS domain."
)
