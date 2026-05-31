import hashlib
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field

from config.logging import get_logger, utc_now_iso
from config.utils import document_id_from_key
from domain.exceptions import ChunkExplosionError
from domain.models import DocumentRegistryEntry, IngestionRun, RegistryStatus, SourceObject
from infrastructure.aws.dynamodb_registry import DynamoDBProcessingRegistry
from infrastructure.opensearch.indexer import OpenSearchIndexer
from ingestion.chunkers.hierarchical import HierarchicalChunker
from ingestion.chunkers.metrics import log_chunk_metrics, section_token_stats
from ingestion.embeddings.provider import EmbeddingProvider
from ingestion.enrichers.chunks import ChunkEnricher
from ingestion.enrichers.document import DocumentEnricher
from ingestion.enrichers.metadata import MetadataExtractor
from ingestion.loaders.s3_loader import S3DocumentLoader
from ingestion.parsers.factory import ParserFactory
from ingestion.pipeline_log import log_gap, log_stage
from ingestion.preprocessors.pipeline import DocumentPreprocessor
from ingestion.writers.s3_writer import S3ProcessedDocumentWriter

logger = get_logger(__name__)


def compute_document_hash(content: bytes | str) -> str:
    data = content if isinstance(content, bytes) else content.encode("utf-8")
    return hashlib.sha256(data).hexdigest()


@dataclass
class _DocumentResult:
    written: int = 0
    embedded: int = 0
    indexed: int = 0
    skipped: bool = False
    error: str | None = None
    warnings: list[str] = field(default_factory=list)


class DocumentIngestionPipeline:
    """
    Single orchestration class — read this file to understand ingestion:

        Load → PyMuPDF/Text Parse → Heading Extraction → Preprocess → Metadata
        → Document Summary → Hierarchical Chunk → Enrich → Embed → S3 → OpenSearch

    Documents process one-at-a-time by default (safe on t3.medium EC2).
    Set INGESTION_MAX_WORKERS>1 only on larger instances.
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
        max_workers: int = 1,
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
        self._max_workers = max(1, max_workers)

    def run(self, run: IngestionRun) -> None:
        run_started = time.perf_counter()

        run.phase = "scanning"
        sources = list(self._loader.list_documents())
        if run.max_documents:
            sources = sources[: run.max_documents]

        if not sources:
            log_gap("load", document_key=self._loader.bucket, reason="no_documents_found")

        self._indexer.ensure_index(self._embeddings.dimension)

        pending: list[SourceObject] = []
        for source in sources:
            if not run.force_reprocess and self._registry.is_unchanged(source):
                run.documents_skipped += 1
                logger.info("document_skipped", key=source.key, reason="unchanged_etag")
                continue
            pending.append(source)

        if pending:
            run.phase = "processing"
            total = len(pending)
            logger.info(
                "document_processing_start",
                count=total,
                workers=self._max_workers,
                mode="sequential" if self._max_workers == 1 else "parallel",
            )

            if self._max_workers == 1:
                for index, source in enumerate(pending, start=1):
                    logger.info(
                        "document_progress",
                        current=index,
                        total=total,
                        key=source.key,
                    )
                    result = self._process_document_safe(source, run.force_reprocess)
                    self._apply_result(run, source, result)
            else:
                with ThreadPoolExecutor(max_workers=self._max_workers) as executor:
                    futures = {
                        executor.submit(
                            self._process_document_safe,
                            source,
                            run.force_reprocess,
                        ): source
                        for source in pending
                    }
                    for future in as_completed(futures):
                        source = futures[future]
                        try:
                            result = future.result()
                        except Exception as exc:
                            result = _DocumentResult(error=str(exc))
                            logger.exception("document_failed", key=source.key)
                        self._apply_result(run, source, result)

        run.phase = "completed"
        logger.info(
            "pipeline_metrics",
            documents_processed=run.documents_processed,
            documents_skipped=run.documents_skipped,
            failed_documents=run.documents_failed,
            chunks_created=run.chunks_written,
            embeddings_generated=run.embeddings_generated,
            processing_duration_ms=round((time.perf_counter() - run_started) * 1000, 2),
            max_workers=self._max_workers,
        )

    def _apply_result(
        self,
        run: IngestionRun,
        source: SourceObject,
        result: _DocumentResult,
    ) -> None:
        if result.error:
            run.documents_failed += 1
            run.errors.append(f"{source.key}: {result.error}")
            logger.error("document_failed", key=source.key, error=result.error)
        elif result.skipped:
            run.documents_skipped += 1
        else:
            run.documents_processed += 1
            run.chunks_written += result.written
            run.embeddings_generated += result.embedded
            for warning in result.warnings:
                run.errors.append(f"{source.key}: {warning}")

    def _process_document_safe(
        self,
        source: SourceObject,
        force_reprocess: bool,
    ) -> _DocumentResult:
        try:
            return self._process_document(source, force_reprocess)
        except ChunkExplosionError as exc:
            logger.error(
                "chunk_explosion_error",
                key=source.key,
                chunk_count=exc.chunk_count,
                limit=exc.limit,
            )
            self._registry.upsert(
                DocumentRegistryEntry(
                    document_id=document_id_from_key(source.key),
                    source_key=source.key,
                    etag=source.etag,
                    last_modified=source.last_modified.isoformat(),
                    status=RegistryStatus.FAILED,
                    error_message=str(exc),
                    chunk_count=exc.chunk_count,
                )
            )
            return _DocumentResult(error=str(exc))
        except Exception as exc:
            logger.exception("document_exception", key=source.key)
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
            return _DocumentResult(error=str(exc))

    def _process_document(
        self,
        source: SourceObject,
        force_reprocess: bool,
    ) -> _DocumentResult:
        key = source.key
        doc_started = time.perf_counter()
        result = _DocumentResult()

        with log_stage("load", document_key=key, size=source.size):
            raw = self._loader.load(source)

        document_hash = compute_document_hash(raw.content)
        if not force_reprocess and self._registry.is_unchanged(source, document_hash):
            logger.info("document_skipped", key=key, reason="unchanged_hash")
            result.skipped = True
            return result

        with log_stage("parse", document_key=key):
            parsed = self._parser.parse(raw)

        with log_stage("preprocess", document_key=key):
            document = self._preprocessor.process(parsed)
            if not document.text.strip():
                log_gap("preprocess", document_key=key, reason="empty_document")
                return result

        with log_stage("extract_metadata", document_key=key):
            metadata = self._metadata.extract(document)

        self._registry.upsert(
            DocumentRegistryEntry(
                document_id=metadata.document_id,
                source_key=key,
                etag=source.etag,
                last_modified=source.last_modified.isoformat(),
                status=RegistryStatus.PROCESSING,
                document_hash=document_hash,
            )
        )

        with log_stage("document_summary", document_key=key):
            metadata.document_summary = self._document_enricher.summarize(document, metadata)

        section_stats = section_token_stats(document.sections, self._chunker._settings)
        section_count = (
            sum(1 for _ in HierarchicalChunker.iter_leaves(document.sections))
            if document.sections
            else 0
        )

        with log_stage("chunk", document_key=key):
            chunks = self._chunker.chunk(document, metadata)
            if not chunks:
                log_gap("chunk", document_key=key, reason="zero_chunks")
                return result

        log_chunk_metrics(
            source_key=key,
            total_pages=document.total_pages,
            section_count=section_count,
            section_token_stats=section_stats,
            chunks=chunks,
        )

        with log_stage("enrich", document_key=key, chunk_count=len(chunks)):
            chunks = self._enricher.enrich(chunks, metadata)

        embed_started = time.perf_counter()
        with log_stage("embed", document_key=key, chunk_count=len(chunks)):
            vectors = self._embeddings.embed_documents(chunks, metadata)
            if len(vectors) != len(chunks):
                log_gap(
                    "embed",
                    document_key=key,
                    reason="vector_count_mismatch",
                    chunks=len(chunks),
                    vectors=len(vectors),
                )
                return result
            for chunk, vector in zip(chunks, vectors, strict=True):
                chunk.embedding = vector

        embedding_duration_ms = round((time.perf_counter() - embed_started) * 1000, 2)
        logger.info(
            "embedding_metrics",
            source_key=key,
            chunk_count=len(chunks),
            embedding_duration_ms=embedding_duration_ms,
        )

        with log_stage("store_s3", document_key=key, chunk_count=len(chunks)):
            result.written = self._writer.write(document, metadata, chunks)

        self._registry.upsert(
            DocumentRegistryEntry(
                document_id=metadata.document_id,
                source_key=key,
                etag=source.etag,
                last_modified=source.last_modified.isoformat(),
                status=RegistryStatus.STORED,
                document_hash=document_hash,
                processed_at=utc_now_iso(),
                chunk_count=len(chunks),
            )
        )

        index_started = time.perf_counter()
        with log_stage("store_opensearch", document_key=key, chunk_count=len(chunks)):
            index_result = self._indexer.index(chunks, key)

        indexing_duration_ms = round((time.perf_counter() - index_started) * 1000, 2)
        logger.info(
            "indexing_metrics",
            source_key=key,
            chunks_indexed=index_result.indexed,
            indexing_duration_ms=indexing_duration_ms,
        )

        result.indexed = index_result.indexed
        result.embedded = len(vectors)

        index_error: str | None = None
        if index_result.batch_errors:
            index_error = "; ".join(index_result.batch_errors)
            result.warnings.append(f"partial indexing: {index_error}")

        self._registry.upsert(
            DocumentRegistryEntry(
                document_id=metadata.document_id,
                source_key=key,
                etag=source.etag,
                last_modified=source.last_modified.isoformat(),
                status=RegistryStatus.INDEXED,
                document_hash=document_hash,
                processed_at=utc_now_iso(),
                indexed_at=utc_now_iso(),
                chunk_count=len(chunks),
                embedding_count=len(vectors),
                error_message=index_error,
            )
        )

        logger.info(
            "document_metrics",
            source_key=key,
            pages=document.total_pages,
            section_count=section_count,
            chunks_created=result.written,
            embeddings_generated=result.embedded,
            opensearch_indexed=result.indexed,
            opensearch_failed=index_result.failed,
            embedding_duration_ms=embedding_duration_ms,
            indexing_duration_ms=indexing_duration_ms,
            processing_duration_ms=round((time.perf_counter() - doc_started) * 1000, 2),
        )
        return result
