from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from config.container import get_container
from config.logging import NotFoundError, setup_logging
from config.settings import get_settings
from domain.models import JobStatus
from ingestion.runner.launcher import IngestionLauncher


class IngestionRunRequest(BaseModel):
    prefix: str | None = None
    max_documents: int | None = Field(default=None, ge=1)
    force_reprocess: bool = False


class IngestionJobResponse(BaseModel):
    job_id: str
    status: JobStatus


class IngestionStatusResponse(BaseModel):
    job_id: str
    status: JobStatus
    phase: str | None
    documents_processed: int
    documents_skipped: int
    documents_failed: int
    chunks_written: int
    embeddings_generated: int
    errors: list[str]


def get_launcher() -> IngestionLauncher:
    return IngestionLauncher()


LauncherDep = Annotated[IngestionLauncher, Depends(get_launcher)]


@asynccontextmanager
async def lifespan(_: FastAPI):
    settings = get_settings()
    setup_logging(settings.log_level)
    get_container()
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name, lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list(),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "service": settings.app_name}

    @app.post("/ingestion/run", response_model=IngestionJobResponse)
    def run_ingestion(body: IngestionRunRequest, launcher: LauncherDep) -> IngestionJobResponse:
        job = launcher.start(
            prefix=body.prefix,
            max_documents=body.max_documents,
            force_reprocess=body.force_reprocess,
        )
        return IngestionJobResponse(job_id=job.job_id, status=job.status)

    @app.get("/ingestion/status", response_model=IngestionStatusResponse)
    def ingestion_status(
        launcher: LauncherDep,
        job_id: str = Query(...),
    ) -> IngestionStatusResponse:
        job = launcher.get_status(job_id)
        if job is None:
            raise NotFoundError(f"Job {job_id} not found")
        return IngestionStatusResponse(
            job_id=job.job_id,
            status=job.status,
            phase=job.phase,
            documents_processed=job.documents_processed,
            documents_skipped=job.documents_skipped,
            documents_failed=job.documents_failed,
            chunks_written=job.chunks_written,
            embeddings_generated=job.embeddings_generated,
            errors=job.errors,
        )

    @app.exception_handler(NotFoundError)
    async def not_found_handler(_, exc: NotFoundError):
        from fastapi.responses import JSONResponse

        return JSONResponse(status_code=404, content={"detail": str(exc)})

    return app


app = create_app()
