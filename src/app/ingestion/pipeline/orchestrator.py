import asyncio
from collections.abc import Callable

from app.observability.logging import get_logger
from app.ingestion.chunking.hierarchical_chunker import HierarchicalChunker
from app.ingestion.embeddings.service import EmbeddingService
from app.ingestion.indexing.opensearch_indexer import OpenSearchIndexer
from app.ingestion.ports.loader import IDocumentLoader
from app.ingestion.domain.job import IngestionJob
from app.ingestion.parsers.registry import ParserRegistry
from app.ingestion.preprocessors.pipeline import PreprocessorPipeline
from app.ingestion.pipeline.metadata import MetadataExtractor

logger = get_logger(__name__)


class IngestionOrchestrator:
    def __init__(
        self,
        loader: IDocumentLoader,
        parser_registry: ParserRegistry,
        preprocessor: PreprocessorPipeline,
        metadata_extractor: MetadataExtractor,
        chunker: HierarchicalChunker,
        embedding_service: EmbeddingService,
        indexer: OpenSearchIndexer,
    ) -> None:
        self._loader = loader
        self._parser = parser_registry
        self._preprocessor = preprocessor
        self._metadata_extractor = metadata_extractor
        self._chunker = chunker
        self._embedding_service = embedding_service
        self._indexer = indexer

    async def run(
        self,
        job: IngestionJob,
        *,
        prefix: str | None = None,
        max_documents: int | None = None,
        reindex: bool = False,
        on_progress: Callable[[IngestionJob], None] | None = None,
    ) -> None:
        def tick(phase: str) -> None:
            job.phase = phase
            if on_progress:
                on_progress(job)

        tick("loading")
        documents = await asyncio.to_thread(
            lambda: list(self._loader.iter_documents(prefix, max_documents))
        )

        if reindex:
            tick("reindex_mode")

        self._indexer.ensure_index(self._embedding_service.dimension)

        for raw in documents:
            tick(f"parsing:{raw.key}")
            parsed = await asyncio.to_thread(self._parser.parse, raw)

            tick(f"preprocessing:{raw.key}")
            preprocessed = await asyncio.to_thread(self._preprocessor.process, parsed)

            doc_meta = self._metadata_extractor.document_metadata(raw.key)
            tick(f"chunking:{raw.key}")
            chunks = await asyncio.to_thread(self._chunker.chunk, preprocessed, doc_meta)
            chunks = self._metadata_extractor.enrich_chunks(chunks)

            if not chunks:
                job.documents_processed += 1
                continue

            tick(f"embedding:{raw.key}")
            vectors = await asyncio.to_thread(
                self._embedding_service.embed_texts,
                [c.content for c in chunks],
            )

            tick(f"indexing:{raw.key}")
            indexed = await asyncio.to_thread(self._indexer.bulk_upsert, chunks, vectors)

            job.documents_processed += 1
            job.chunks_indexed += indexed
            logger.info(
                "document_ingested",
                key=raw.key,
                chunks=len(chunks),
                indexed=indexed,
            )

        tick("completed")
