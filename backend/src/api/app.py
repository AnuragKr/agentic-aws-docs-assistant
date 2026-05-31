from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from config.container import get_container
from config.logging import setup_logging
from config.settings import get_settings
from domain.models import IngestionRun


class IngestionRunRequest(BaseModel):
    prefix: str | None = None
    max_documents: int | None = Field(default=None, ge=1)
    force_reprocess: bool = False


class IngestionRunResponse(BaseModel):
    phase: str | None
    documents_processed: int
    documents_skipped: int
    documents_failed: int
    chunks_written: int
    embeddings_generated: int
    errors: list[str]


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

    @app.post("/ingestion/run", response_model=IngestionRunResponse)
    def run_ingestion(body: IngestionRunRequest) -> IngestionRunResponse:
        run = IngestionRun(
            prefix=body.prefix,
            max_documents=body.max_documents,
            force_reprocess=body.force_reprocess,
        )
        get_container().pipeline.run(run)
        return IngestionRunResponse(
            phase=run.phase,
            documents_processed=run.documents_processed,
            documents_skipped=run.documents_skipped,
            documents_failed=run.documents_failed,
            chunks_written=run.chunks_written,
            embeddings_generated=run.embeddings_generated,
            errors=run.errors,
        )

    return app


app = create_app()
