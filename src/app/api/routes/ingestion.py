from fastapi import APIRouter, Query

from app.api.deps import JobManagerDep
from app.api.schemas.ingestion import (
    IngestionJobResponse,
    IngestionStartRequest,
    IngestionStatusResponse,
)
from app.core.exceptions import NotFoundError

router = APIRouter(prefix="/ingestion", tags=["ingestion"])


@router.post("/start", response_model=IngestionJobResponse)
async def start_ingestion(
    body: IngestionStartRequest,
    job_manager: JobManagerDep,
) -> IngestionJobResponse:
    job = await job_manager.start(prefix=body.prefix, max_documents=body.max_documents)
    return IngestionJobResponse(job_id=job.job_id, status=job.status)


@router.post("/reindex", response_model=IngestionJobResponse)
async def reindex(
    body: IngestionStartRequest,
    job_manager: JobManagerDep,
) -> IngestionJobResponse:
    job = await job_manager.start(
        prefix=body.prefix,
        max_documents=body.max_documents,
        reindex=True,
    )
    return IngestionJobResponse(job_id=job.job_id, status=job.status)


@router.get("/status", response_model=IngestionStatusResponse)
def ingestion_status(
    job_manager: JobManagerDep,
    job_id: str = Query(...),
) -> IngestionStatusResponse:
    job = job_manager.get(job_id)
    if job is None:
        raise NotFoundError(f"Job {job_id} not found")
    return IngestionStatusResponse(
        job_id=job.job_id,
        status=job.status,
        phase=job.phase,
        documents_processed=job.documents_processed,
        chunks_indexed=job.chunks_indexed,
        errors=job.errors,
    )
