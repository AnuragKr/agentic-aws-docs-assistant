import time

from config.logging import get_logger
from config.settings import Settings
from generation.exceptions import GenerationError
from generation.models import GenerationRequest, GenerationResponse, SourceReference
from generation.prompt_builder import PromptBuilder
from generation.providers.base import GenerationProvider

logger = get_logger(__name__)


class GenerationService:
    """
    Prompt construction and LLM invocation only.

    Retrieval and reranking are handled separately by RetrievalService.
    """

    def __init__(
        self,
        provider: GenerationProvider,
        prompt_builder: PromptBuilder,
        settings: Settings,
    ) -> None:
        self._provider = provider
        self._prompt_builder = prompt_builder
        self._settings = settings

    def generate(self, request: GenerationRequest) -> GenerationResponse:
        question = request.question.strip()
        if not question:
            raise GenerationError("Question must not be empty")

        chunks = request.retrieved_chunks
        system_prompt, user_prompt = self._prompt_builder.build(question, chunks)
        estimated_tokens = self._prompt_builder.estimate_prompt_tokens(question, chunks)

        logger.info(
            "generation_start",
            question_len=len(question),
            model_id=self._provider.model_id,
            retrieved_chunk_count=len(chunks),
            reranked_chunk_count=len(chunks),
            estimated_prompt_tokens=estimated_tokens,
        )

        started = time.perf_counter()
        try:
            answer = self._provider.generate(system_prompt, user_prompt)
        except GenerationError:
            raise
        except Exception as exc:
            raise GenerationError(f"Generation failed: {exc}") from exc

        latency_ms = round((time.perf_counter() - started) * 1000, 2)
        sources = self._build_sources(chunks)

        logger.info(
            "generation_complete",
            question_len=len(question),
            model_id=self._provider.model_id,
            retrieved_chunk_count=len(chunks),
            reranked_chunk_count=len(chunks),
            estimated_prompt_tokens=estimated_tokens,
            generation_latency_ms=latency_ms,
            source_count=len(sources),
        )

        return GenerationResponse(
            answer=answer,
            sources=sources,
            model_id=self._provider.model_id,
            latency_ms=latency_ms,
        )

    @staticmethod
    def _build_sources(chunks: list) -> list[SourceReference]:
        seen: set[tuple[str, int | None, str | None]] = set()
        sources: list[SourceReference] = []
        for chunk in chunks:
            document_name = chunk.document_title or chunk.title or chunk.source_file or chunk.document_id
            section_title = chunk.section or chunk.subsection
            key = (document_name, chunk.page_number, section_title)
            if key in seen:
                continue
            seen.add(key)
            sources.append(
                SourceReference(
                    document_name=document_name,
                    page_number=chunk.page_number,
                    section_title=section_title,
                )
            )
        return sources
