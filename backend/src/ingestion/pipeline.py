from collections.abc import Callable

from config.logging import get_logger, utc_now_iso
from config.utils import document_id_from_key
from domain.models import DocumentRegistryEntry, IngestionJob, RegistryStatus, SourceObject
from infrastructure.aws.dynamodb_registry import DynamoDBProcessingRegistry
from ingestion.chunkers.hierarchical import HierarchicalChunker
from ingestion.embeddings.provider import EmbeddingProvider
from ingestion.enrichers.chunks import ChunkEnricher
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

        Load → Docling Parse → Preprocess → Metadata → Chunk → Enrich → Embed → Store
    """

    def __init__(
        self,
        loader: S3DocumentLoader,
        parser_factory: ParserFactory,
        preprocessor: DocumentPreprocessor,
        metadata_extractor: MetadataExtractor,
        chunker: HierarchicalChunker,
        chunk_enricher: ChunkEnricher,
        embedding_provider: EmbeddingProvider,
        writer: S3ProcessedDocumentWriter,
        registry: DynamoDBProcessingRegistry,
    ) -> None:
        self._loader = loader
        self._parser = parser_factory
        self._preprocessor = preprocessor
        self._metadata = metadata_extractor
        self._chunker = chunker
        self._enricher = chunk_enricher
        self._embeddings = embedding_provider
        self._writer = writer
        self._registry = registry

    def run(
        self,
        job: IngestionJob,
        *,
        on_progress: Callable[[IngestionJob], None] | None = None,
    ) -> None:
        def tick(phase: str) -> None:
            job.phase = phase
            if on_progress:
                on_progress(job)

        tick("scanning")
        sources = list(self._loader.list_documents(job.prefix))
        if job.max_documents:
            sources = sources[: job.max_documents]

        if not sources:
            log_gap("load", document_key=job.prefix or "", reason="no_documents_found")

        for source in sources:
            if not job.force_reprocess and self._registry.is_unchanged(source):
                job.documents_skipped += 1
                logger.info("document_skipped", key=source.key, reason="unchanged")
                continue

            try:
                written = self._process_document(source, tick)
                job.documents_processed += 1
                job.chunks_written += written
            except Exception as exc:
                job.documents_failed += 1
                job.errors.append(f"{source.key}: {exc}")
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
            "pipeline_complete",
            job_id=job.job_id,
            processed=job.documents_processed,
            skipped=job.documents_skipped,
            failed=job.documents_failed,
            chunks_written=job.chunks_written,
        )

    def _process_document(
        self,
        source: SourceObject,
        tick: Callable[[str], None],
    ) -> int:
        key = source.key

        # 1. Load document
        tick("load")
        with log_stage("load", document_key=key, size=source.size):
            raw = self._loader.load(source)

        # 2. Docling parse (structure + hierarchy)
        tick("docling")
        with log_stage("docling", document_key=key):
            parsed = self._parser.parse(raw)

        # 3. Preprocess
        tick("preprocess")
        with log_stage("preprocess", document_key=key):
            document = self._preprocessor.process(parsed)
            if not document.text.strip():
                log_gap("preprocess", document_key=key, reason="empty_document")
                return 0

        # 4. Extract metadata
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

        # 5. Hierarchical chunking
        tick("chunk")
        with log_stage("chunk", document_key=key):
            chunks = self._chunker.chunk(document, metadata)
            if not chunks:
                log_gap("chunk", document_key=key, reason="zero_chunks")
                return 0

        # 6. Chunk enrichment
        tick("enrich")
        with log_stage("enrich", document_key=key, chunk_count=len(chunks)):
            chunks = self._enricher.enrich(chunks, metadata)

        # 7. Embedding generation
        tick("embed")
        with log_stage("embed", document_key=key, chunk_count=len(chunks)):
            vectors = self._embeddings.embed_documents([c.content for c in chunks])
            if len(vectors) != len(chunks):
                log_gap(
                    "embed",
                    document_key=key,
                    reason="vector_count_mismatch",
                    chunks=len(chunks),
                    vectors=len(vectors),
                )
                return 0
            for chunk, vector in zip(chunks, vectors, strict=True):
                chunk.embedding = vector

        # 8. Store results (S3)
        tick("store")
        with log_stage("store", document_key=key, chunk_count=len(chunks)):
            written = self._writer.write(document, metadata, chunks)

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
        return written
