from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from config.container import get_container
from config.logging import get_logger, setup_logging
from config.settings import get_settings
from config.warmup import warmup_models
from domain.models import IngestionRun, RetrievedChunk
from generation.exceptions import GenerationError
from generation.models import GenerationRequest, GenerationResponse
from retrieval.filters import SearchFilters

logger = get_logger(__name__)


class IngestionRunRequest(BaseModel):
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


class SearchFiltersRequest(BaseModel):
    service: str | None = None
    service_category: str | None = None
    section: str | None = None
    subsection: str | None = None
    topics: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)


class SearchRequest(BaseModel):
    query: str = Field(min_length=1)
    top_k: int = Field(default=5, ge=1, le=20)
    filters: SearchFiltersRequest | None = None


class SearchResponse(BaseModel):
    query: str
    results: list[RetrievedChunk]


class GenerateRequest(BaseModel):
    question: str = Field(min_length=1)
    chunks: list[RetrievedChunk] = Field(default_factory=list)


class AskRequest(BaseModel):
    question: str = Field(min_length=1)
    top_k: int = Field(default=5, ge=1, le=20)
    filters: SearchFiltersRequest | None = None


class AskResponse(BaseModel):
    query: str
    answer: str
    sources: list[dict]
    model_id: str
    latency_ms: float
    retrieval_count: int


@asynccontextmanager
async def lifespan(_: FastAPI):
    settings = get_settings()
    setup_logging(settings)
    get_container()
    warmup_models()
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
    def health() -> dict:
        """Fast liveness probe — no OpenSearch or ML model calls."""
        return {"status": "ok", "service": settings.app_name}

    @app.get("/health/ready")
    def health_ready() -> dict:
        """Readiness probe — checks OpenSearch with a short timeout."""
        container = get_container()
        opensearch = container.opensearch_store.ping()
        ready = opensearch.get("reachable") and opensearch.get("index_exists")
        return {
            "status": "ok" if ready else "degraded",
            "service": settings.app_name,
            "opensearch": opensearch,
            "reranker_enabled": settings.reranker_enabled,
        }

    @app.post("/ingestion/run", response_model=IngestionRunResponse)
    def run_ingestion(body: IngestionRunRequest) -> IngestionRunResponse:
        run = IngestionRun(
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

    @app.post("/search", response_model=SearchResponse)
    def search(body: SearchRequest) -> SearchResponse:
        query = body.query.strip()
        if not query:
            raise HTTPException(status_code=400, detail="Query must not be empty")

        filters = None
        if body.filters and not _filters_empty(body.filters):
            filters = SearchFilters.model_validate(body.filters.model_dump())

        try:
            results = get_container().retrieval_service.search(
                query,
                top_k=body.top_k,
                filters=filters,
            )
        except Exception as exc:
            logger.exception("search_failed", query=query[:80])
            raise HTTPException(status_code=503, detail=f"Search failed: {exc}") from exc

        return SearchResponse(query=query, results=results)

    @app.post("/generate", response_model=GenerationResponse)
    def generate(body: GenerateRequest) -> GenerationResponse:
        question = body.question.strip()
        if not question:
            raise HTTPException(status_code=400, detail="Question must not be empty")
        if not body.chunks:
            raise HTTPException(
                status_code=400,
                detail="Retrieved chunks are required. Call /search first or use /ask.",
            )

        try:
            return get_container().generation_service.generate(
                GenerationRequest(question=question, retrieved_chunks=body.chunks)
            )
        except GenerationError as exc:
            logger.exception("generation_failed", question_len=len(question))
            raise HTTPException(status_code=503, detail=str(exc)) from exc

    @app.post("/ask", response_model=AskResponse)
    def ask(body: AskRequest) -> AskResponse:
        """Retrieve (OpenSearch + rerank) then generate an answer with citations."""
        question = body.question.strip()
        if not question:
            raise HTTPException(status_code=400, detail="Question must not be empty")

        container = get_container()
        settings = container.settings
        top_k = body.top_k or settings.generation_rerank_top_k

        filters = None
        if body.filters and not _filters_empty(body.filters):
            filters = SearchFilters.model_validate(body.filters.model_dump())

        try:
            chunks = container.retrieval_service.search(
                question,
                top_k=top_k,
                filters=filters,
            )
            generation = container.generation_service.generate(
                GenerationRequest(question=question, retrieved_chunks=chunks)
            )
        except GenerationError as exc:
            logger.exception("ask_generation_failed", question_len=len(question))
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        except Exception as exc:
            logger.exception("ask_failed", question_len=len(question))
            raise HTTPException(status_code=503, detail=f"Ask failed: {exc}") from exc

        return AskResponse(
            query=question,
            answer=generation.answer,
            sources=[source.model_dump() for source in generation.sources],
            model_id=generation.model_id,
            latency_ms=generation.latency_ms,
            retrieval_count=len(chunks),
        )

    return app


def _filters_empty(filters: SearchFiltersRequest) -> bool:
    return SearchFilters.model_validate(filters.model_dump()).is_empty()


app = create_app()
