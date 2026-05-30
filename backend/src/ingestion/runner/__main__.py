import argparse
import sys

from config.container import IngestionService, get_container
from config.logging import setup_logging
from domain.models import JobStatus


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Independent document ingestion worker")
    parser.add_argument("--job-id", required=True, help="Ingestion job identifier")
    args = parser.parse_args(argv)

    container = get_container()
    setup_logging(container.settings.log_level)

    IngestionService(container).run_job(args.job_id)
    job = container.job_store.get(args.job_id)
    return 0 if job and job.status == JobStatus.COMPLETED else 1


if __name__ == "__main__":
    sys.exit(main())
