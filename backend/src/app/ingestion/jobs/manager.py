import asyncio
from datetime import datetime, timezone

from app.core.container import AppContainer
from app.observability.logging import get_logger
from app.ingestion.domain.job import IngestionJob, JobStatus
from app.ingestion.pipeline.orchestrator import IngestionOrchestrator

logger = get_logger(__name__)


class JobManager:
    def __init__(self, container: AppContainer) -> None:
        self._container = container
        self._jobs: dict[str, IngestionJob] = {}

    @property
    def orchestrator(self) -> IngestionOrchestrator:
        return self._container.orchestrator

    def get(self, job_id: str) -> IngestionJob | None:
        return self._jobs.get(job_id)

    async def start(
        self,
        *,
        prefix: str | None = None,
        max_documents: int | None = None,
        reindex: bool = False,
    ) -> IngestionJob:
        job = IngestionJob(status=JobStatus.PENDING, phase="queued")
        self._jobs[job.job_id] = job
        asyncio.create_task(
            self._run_job(job, prefix=prefix, max_documents=max_documents, reindex=reindex)
        )
        logger.info("ingestion_job_started", job_id=job.job_id, reindex=reindex)
        return job

    async def _run_job(
        self,
        job: IngestionJob,
        *,
        prefix: str | None,
        max_documents: int | None,
        reindex: bool,
    ) -> None:
        job.status = JobStatus.RUNNING
        try:
            await self.orchestrator.run(
                job,
                prefix=prefix,
                max_documents=max_documents,
                reindex=reindex,
                on_progress=lambda j: None,
            )
            job.status = JobStatus.COMPLETED
            job.finished_at = datetime.now(timezone.utc)
            logger.info(
                "ingestion_job_completed",
                job_id=job.job_id,
                documents=job.documents_processed,
                chunks=job.chunks_indexed,
            )
        except Exception as exc:
            job.status = JobStatus.FAILED
            job.phase = "failed"
            job.errors.append(str(exc))
            job.finished_at = datetime.now(timezone.utc)
            logger.exception("ingestion_job_failed", job_id=job.job_id)
