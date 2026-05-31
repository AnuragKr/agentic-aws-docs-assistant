import time
from collections.abc import Callable

from config.logging import get_logger, utc_now_iso
from config.utils import document_id_from_key
from domain.models import DocumentRegistryEntry, IngestionRun, RegistryStatus, SourceObject
from infrastructure.aws.dynamodb_registry import DynamoDBProcessingRegistry
from infrastructure.opensearch.indexer import OpenSearchIndexer
from ingestion.chunkers.hierarchical import HierarchicalChunker
from ingestion.embeddings.provider import EmbeddingProvider
from ingestion.enrichers.chunks import ChunkEnricher, build_embedding_text
from ingestion.enrichers.document import DocumentEnricher
from ingestion.enrichers.metadata import MetadataExtractor
from ingestion.loaders.s3_loader import S3DocumentLoader
from ingestion.parsers.factory import ParserFactory
from ingestion.pipeline_log import log_gap, log_stage
from ingestion.preprocessors.pipeline import DocumentPreprocessor
from ingestion.writers.s3_writer import S3ProcessedDocumentWriter

logger = get_logger(__name__)


class DocumentIngestionPipeline:
    """
    Single orchestration class — read this file to understand ingestion:

        Load → Preprocess → Extract Metadata → Document Summary → Chunk
        → Enrich → Embed → Store → Update Registry
    """

    def __init__(
        self,
        loader: S3DocumentLoader,
        parser_factory: ParserFactory,
        preprocessor: DocumentPreprocessor,
        metadata_extractor: MetadataExtractor,
        document_enricher: DocumentEnricher,
        chunker: HierarchicalChunker,
        chunk_enricher: ChunkEnricher,
        embedding_provider: EmbeddingProvider,
        writer: S3ProcessedDocumentWriter,
        indexer: OpenSearchIndexer,
        registry: DynamoDBProcessingRegistry,
    ) -> None:
        self._loader = loader
        self._parser = parser_factory
        self._preprocessor = preprocessor
        self._metadata = metadata_extractor
        self._document_enricher = document_enricher
        self._chunker = chunker
        self._enricher = chunk_enricher
        self._embeddings = embedding_provider
        self._writer = writer
        self._indexer = indexer
        self._registry = registry

    def run(self, run: IngestionRun) -> None:
        run_started = time.perf_counter()

        def tick(phase: str) -> None:
            run.phase = phase

        tick("scanning")
        sources = list(self._loader.list_documents())
        if run.max_documents:
            sources = sources[: run.max_documents]

        if not sources:
            log_gap("load", document_key=self._loader.bucket, reason="no_documents_found")

        self._indexer.ensure_index(self._embeddings.dimension)

        for source in sources:
            if not run.force_reprocess and self._registry.is_unchanged(source):
                run.documents_skipped += 1
                logger.info("document_skipped", key=source.key, reason="unchanged")
                continue

            try:
                written, embedded = self._process_document(source, tick)
                run.documents_processed += 1
                run.chunks_written += written
                run.embeddings_generated += embedded
            except Exception as exc:
                run.documents_failed += 1
                run.errors.append(f"{source.key}: {exc}")
                logger.exception("document_failed", key=source.key)
                self._registry.upsert(
                    DocumentRegistryEntry(
                        document_id=document_id_from_key(source.key),
                        source_key=source.key,
                        etag=source.etag,
                        last_modified=source.last_modified.isoformat(),
                        status=RegistryStatus.FAILED,
                        error_message=str(exc),
                    )
                )

        tick("completed")
        logger.info(
            "pipeline_metrics",
            documents_processed=run.documents_processed,
            documents_skipped=run.documents_skipped,
            failed_documents=run.documents_failed,
            chunks_created=run.chunks_written,
            embeddings_generated=run.embeddings_generated,
            processing_duration_ms=round((time.perf_counter() - run_started) * 1000, 2),
        )

    def _process_document(
        self,
        source: SourceObject,
        tick: Callable[[str], None],
    ) -> tuple[int, int]:
        key = source.key
        doc_started = time.perf_counter()

        tick("load")
        with log_stage("load", document_key=key, size=source.size):
            raw = self._loader.load(source)

        tick("docling")
        with log_stage("docling", document_key=key):
            parsed = self._parser.parse(raw)

        tick("preprocess")
        with log_stage("preprocess", document_key=key):
            document = self._preprocessor.process(parsed)
            if not document.text.strip():
                log_gap("preprocess", document_key=key, reason="empty_document")
                return 0, 0

        tick("extract_metadata")
        with log_stage("extract_metadata", document_key=key):
            metadata = self._metadata.extract(document)

        self._registry.upsert(
            DocumentRegistryEntry(
                document_id=metadata.document_id,
                source_key=key,
                etag=source.etag,
                last_modified=source.last_modified.isoformat(),
                status=RegistryStatus.PROCESSING,
            )
        )

        tick("document_summary")
        with log_stage("document_summary", document_key=key):
            metadata.document_summary = self._document_enricher.summarize(document, metadata)

        tick("chunk")
        with log_stage("chunk", document_key=key):
            chunks = self._chunker.chunk(document, metadata)
            if not chunks:
                log_gap("chunk", document_key=key, reason="zero_chunks")
                return 0, 0

        tick("enrich")
        with log_stage("enrich", document_key=key, chunk_count=len(chunks)):
            chunks = self._enricher.enrich(chunks, metadata)

        tick("embed")
        with log_stage("embed", document_key=key, chunk_count=len(chunks)):
            embed_texts = [build_embedding_text(c, metadata) for c in chunks]
            vectors = self._embeddings.embed_documents(embed_texts)
            if len(vectors) != len(chunks):
                log_gap(
                    "embed",
                    document_key=key,
                    reason="vector_count_mismatch",
                    chunks=len(chunks),
                    vectors=len(vectors),
                )
                return 0, 0
            for chunk, vector in zip(chunks, vectors, strict=True):
                chunk.embedding = vector

        tick("store")
        with log_stage("store", document_key=key, chunk_count=len(chunks)):
            written = self._writer.write(document, metadata, chunks)
            indexed = self._indexer.index(chunks, key)

        self._registry.upsert(
            DocumentRegistryEntry(
                document_id=metadata.document_id,
                source_key=key,
                etag=source.etag,
                last_modified=source.last_modified.isoformat(),
                status=RegistryStatus.COMPLETED,
                processed_at=utc_now_iso(),
            )
        )

        logger.info(
            "document_metrics",
            source_key=key,
            chunks_created=written,
            embeddings_generated=len(vectors),
            opensearch_indexed=indexed,
            processing_duration_ms=round((time.perf_counter() - doc_started) * 1000, 2),
        )
        return written, len(vectors)
