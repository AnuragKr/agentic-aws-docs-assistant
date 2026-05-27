from app.core.config import Settings
from app.core.exceptions import ConfigurationError
from app.ingestion.embeddings.huggingface_provider import HuggingFaceEmbeddingProvider
from app.ingestion.ports.embeddings import IEmbeddingProvider


class EmbeddingProviderFactory:
    @staticmethod
    def create(settings: Settings, provider: IEmbeddingProvider | None = None) -> IEmbeddingProvider:
        if provider is not None:
            return provider

        name = settings.embedding_provider.lower()
        if name in ("huggingface", "sentence-transformers", "local"):
            return HuggingFaceEmbeddingProvider(settings.embedding_model_id)
        if name == "titan":
            raise ConfigurationError(
                "Titan embeddings not configured yet. Use EMBEDDING_PROVIDER=huggingface."
            )
        if name == "openai":
            raise ConfigurationError(
                "OpenAI embeddings not configured yet. Use EMBEDDING_PROVIDER=huggingface."
            )
        raise ConfigurationError(f"Unknown embedding provider: {settings.embedding_provider}")
