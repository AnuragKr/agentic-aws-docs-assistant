from dataclasses import dataclass, field
from functools import cached_property

from app.core.config import Settings, get_settings
from app.ingestion.chunking.hierarchical_chunker import HierarchicalChunker
from app.ingestion.embeddings.factory import EmbeddingProviderFactory
from app.ingestion.embeddings.service import EmbeddingService
from app.ingestion.indexing.opensearch_indexer import OpenSearchIndexer
from app.ingestion.loaders.s3_loader import S3DocumentLoader
from app.ingestion.parsers.registry import ParserRegistry
from app.ingestion.preprocessors.pipeline import PreprocessorPipeline
from app.ingestion.pipeline.orchestrator import IngestionOrchestrator
from app.ingestion.pipeline.metadata import MetadataExtractor
from app.infrastructure.opensearch.client_factory import create_opensearch_client


@dataclass
class AppContainer:
    settings: Settings = field(default_factory=get_settings)

    @cached_property
    def parser_registry(self) -> ParserRegistry:
        return ParserRegistry()

    @cached_property
    def preprocessor(self) -> PreprocessorPipeline:
        return PreprocessorPipeline()

    @cached_property
    def metadata_extractor(self) -> MetadataExtractor:
        return MetadataExtractor(self.settings)

    @cached_property
    def chunker(self) -> HierarchicalChunker:
        return HierarchicalChunker(self.settings)

    @cached_property
    def embedding_service(self) -> EmbeddingService:
        provider = EmbeddingProviderFactory.create(self.settings)
        return EmbeddingService(provider, self.settings)

    @cached_property
    def opensearch_client(self):
        return create_opensearch_client(self.settings)

    @cached_property
    def indexer(self) -> OpenSearchIndexer:
        return OpenSearchIndexer(self.opensearch_client, self.settings)

    @cached_property
    def document_loader(self) -> S3DocumentLoader:
        return S3DocumentLoader(self.settings)

    @cached_property
    def orchestrator(self) -> IngestionOrchestrator:
        return IngestionOrchestrator(
            loader=self.document_loader,
            parser_registry=self.parser_registry,
            preprocessor=self.preprocessor,
            metadata_extractor=self.metadata_extractor,
            chunker=self.chunker,
            embedding_service=self.embedding_service,
            indexer=self.indexer,
        )


_container: AppContainer | None = None


def get_container() -> AppContainer:
    global _container
    if _container is None:
        _container = AppContainer()
    return _container


def reset_container() -> None:
    global _container
    _container = None
