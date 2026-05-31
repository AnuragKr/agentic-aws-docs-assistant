import argparse
import sys

from config.container import get_container
from config.logging import setup_logging
from domain.models import IngestionRun


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run document ingestion")
    parser.add_argument(
        "--prefix",
        default="",
        help="S3 prefix under the raw bucket (default: entire bucket / S3_PREFIX from .env)",
    )
    parser.add_argument("--max-documents", type=int, default=None)
    parser.add_argument("--force-reprocess", action="store_true")
    args = parser.parse_args(argv)

    container = get_container()
    setup_logging(container.settings.log_level)

    run = IngestionRun(
        prefix=args.prefix or None,
        max_documents=args.max_documents,
        force_reprocess=args.force_reprocess,
    )

    try:
        container.pipeline.run(run)
    except Exception as exc:
        print(f"FAILED: {exc}", file=sys.stderr)
        return 1

    print(
        f"Done — processed={run.documents_processed} skipped={run.documents_skipped} "
        f"failed={run.documents_failed} chunks={run.chunks_written} "
        f"embeddings={run.embeddings_generated}"
    )
    if run.errors:
        for err in run.errors:
            print(f"  error: {err}", file=sys.stderr)
    return 0 if run.documents_failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
