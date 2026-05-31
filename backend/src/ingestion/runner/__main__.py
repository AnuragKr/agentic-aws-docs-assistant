import argparse
import sys

from config.container import get_container
from config.logging import setup_logging
from domain.models import IngestionRun


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run document ingestion")
    parser.add_argument("--max-documents", type=int, default=None)
    parser.add_argument("--force-reprocess", action="store_true")
    args = parser.parse_args(argv)

    container = get_container()
    setup_logging(container.settings)

    run = IngestionRun(
        max_documents=args.max_documents,
        force_reprocess=args.force_reprocess,
    )

    exit_code = 1
    try:
        container.pipeline.run(run)
        exit_code = 0 if run.documents_failed == 0 else 1
    except Exception as exc:
        print(f"FAILED: {exc}", file=sys.stderr)
        run.errors.append(str(exc))
    finally:
        print(
            f"Done — processed={run.documents_processed} skipped={run.documents_skipped} "
            f"failed={run.documents_failed} chunks={run.chunks_written} "
            f"embeddings={run.embeddings_generated}",
            flush=True,
        )
        if run.errors:
            for err in run.errors:
                print(f"  error: {err}", file=sys.stderr)

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
