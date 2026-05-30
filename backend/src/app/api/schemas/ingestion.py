from pydantic import BaseModel, Field


class IngestionStartRequest(BaseModel):
    prefix: str | None = Field(default=None, description="S3 prefix override")
    max_documents: int | None = Field(default=None, ge=1)


class IngestionJobResponse(BaseModel):
    job_id: str
    status: str


class IngestionStatusResponse(BaseModel):
    job_id: str
    status: str
    phase: str | None = None
    documents_processed: int = 0
    chunks_indexed: int = 0
    errors: list[str] = Field(default_factory=list)
