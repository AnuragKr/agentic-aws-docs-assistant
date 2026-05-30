import json
from pathlib import Path

from domain.models import IngestionJob


class FileJobStore:
    """Shared job state between API and ingestion worker subprocess."""

    def __init__(self, store_dir: Path) -> None:
        self._dir = store_dir
        self._dir.mkdir(parents=True, exist_ok=True)

    def _path(self, job_id: str) -> Path:
        return self._dir / f"{job_id}.json"

    def create(self, job: IngestionJob) -> IngestionJob:
        self.save(job)
        return job

    def get(self, job_id: str) -> IngestionJob | None:
        path = self._path(job_id)
        if not path.exists():
            return None
        return IngestionJob.model_validate(json.loads(path.read_text()))

    def save(self, job: IngestionJob) -> None:
        self._path(job.job_id).write_text(job.model_dump_json())
