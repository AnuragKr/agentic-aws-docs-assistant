from dataclasses import dataclass, field
from functools import cached_property

from config.settings import Settings, get_settings
from infrastructure.aws.dynamodb_registry import DynamoDBProcessingRegistry
from infrastructure.opensearch.indexer import OpenSearchIndexer, create_opensearch_client
from infrastructure.opensearch.store import OpenSearchStore
from ingestion.chunkers.hierarchical import HierarchicalChunker
from ingestion.embeddings.factory import get_embedding_provider
from ingestion.enrichers.chunks import ChunkEnricher
from ingestion.enrichers.document import DocumentEnricher
from ingestion.enrichers.metadata import MetadataExtractor
from ingestion.loaders.s3_loader import S3DocumentLoader
from ingestion.parsers.factory import ParserFactory
from ingestion.pipeline import DocumentIngestionPipeline
from ingestion.preprocessors.pipeline import DocumentPreprocessor
from ingestion.writers.s3_writer import S3ProcessedDocumentWriter
from generation.prompt_builder import PromptBuilder
from generation.providers.bedrock import BedrockGenerationProvider
from generation.service import GenerationService
from retrieval.reranker import get_reranker
from retrieval.service import RetrievalService


@dataclass
class IngestionContainer:
    settings: Settings = field(default_factory=get_settings)

    @cached_property
    def loader(self) -> S3DocumentLoader:
        s = self.settings
        return S3DocumentLoader(s.s3_raw_bucket, s.aws_region)

    @cached_property
    def parser_factory(self) -> ParserFactory:
        return ParserFactory()

    @cached_property
    def preprocessor(self) -> DocumentPreprocessor:
        return DocumentPreprocessor()

    @cached_property
    def metadata_extractor(self) -> MetadataExtractor:
        return MetadataExtractor(self.settings)

    @cached_property
    def document_enricher(self) -> DocumentEnricher:
        return DocumentEnricher()

    @cached_property
    def chunker(self) -> HierarchicalChunker:
        return HierarchicalChunker(self.settings)

    @cached_property
    def chunk_enricher(self) -> ChunkEnricher:
        return ChunkEnricher()

    @cached_property
    def embedding_provider(self):
        return get_embedding_provider(self.settings)

    @cached_property
    def writer(self) -> S3ProcessedDocumentWriter:
        s = self.settings
        return S3ProcessedDocumentWriter(
            s.s3_processed_bucket, s.aws_region, s.s3_processed_prefix
        )

    @cached_property
    def indexer(self) -> OpenSearchIndexer:
        return OpenSearchIndexer(create_opensearch_client(self.settings), self.settings)

    @cached_property
    def opensearch_store(self) -> OpenSearchStore:
        return OpenSearchStore(create_opensearch_client(self.settings), self.settings)

    @cached_property
    def retrieval_service(self) -> RetrievalService:
        return RetrievalService(
            embeddings=self.embedding_provider,
            store=self.opensearch_store,
            reranker=get_reranker(self.settings),
            settings=self.settings,
        )

    @cached_property
    def prompt_builder(self) -> PromptBuilder:
        return PromptBuilder(context_max_tokens=self.settings.generation_context_max_tokens)

    @cached_property
    def generation_provider(self) -> BedrockGenerationProvider:
        return BedrockGenerationProvider(self.settings)

    @cached_property
    def generation_service(self) -> GenerationService:
        return GenerationService(
            provider=self.generation_provider,
            prompt_builder=self.prompt_builder,
            settings=self.settings,
        )

    @cached_property
    def registry(self) -> DynamoDBProcessingRegistry:
        s = self.settings
        return DynamoDBProcessingRegistry(s.dynamodb_registry_table, s.aws_region)

    @cached_property
    def pipeline(self) -> DocumentIngestionPipeline:
        return DocumentIngestionPipeline(
            loader=self.loader,
            parser_factory=self.parser_factory,
            preprocessor=self.preprocessor,
            metadata_extractor=self.metadata_extractor,
            document_enricher=self.document_enricher,
            chunker=self.chunker,
            chunk_enricher=self.chunk_enricher,
            embedding_provider=self.embedding_provider,
            writer=self.writer,
            indexer=self.indexer,
            registry=self.registry,
            max_workers=self.settings.ingestion_max_workers,
        )


_container: IngestionContainer | None = None


def get_container() -> IngestionContainer:
    global _container
    if _container is None:
        _container = IngestionContainer()
    return _container
