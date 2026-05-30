import os
import subprocess
import sys
from pathlib import Path

from config.container import get_container
from config.logging import get_logger
from domain.models import IngestionJob, JobStatus

logger = get_logger(__name__)


class IngestionLauncher:
    """Starts ingestion as an independent subprocess (not FastAPI BackgroundTask)."""

    def __init__(self) -> None:
        self._container = get_container()
        self._backend_root = Path(__file__).resolve().parents[3]
        self._src_root = self._backend_root / "src"

    def start(
        self,
        *,
        prefix: str | None = None,
        max_documents: int | None = None,
        force_reprocess: bool = False,
    ) -> IngestionJob:
        job = IngestionJob(
            prefix=prefix,
            max_documents=max_documents,
            force_reprocess=force_reprocess,
            status=JobStatus.PENDING,
            phase="queued",
        )
        self._container.job_store.create(job)

        env = os.environ.copy()
        env["PYTHONPATH"] = str(self._src_root)
        cmd = [sys.executable, "-m", "ingestion.runner", "--job-id", job.job_id]
        subprocess.Popen(cmd, cwd=str(self._backend_root), env=env)
        logger.info("ingestion_subprocess_started", job_id=job.job_id)
        return job

    def get_status(self, job_id: str) -> IngestionJob | None:
        return self._container.job_store.get(job_id)
