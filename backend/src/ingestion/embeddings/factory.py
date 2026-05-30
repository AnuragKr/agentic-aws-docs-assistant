from config.settings import Settings
from ingestion.embeddings.huggingface import HuggingFaceEmbeddingProvider
from ingestion.embeddings.provider import EmbeddingProvider, EmbeddingProviderSingleton


def get_embedding_provider(settings: Settings) -> EmbeddingProvider:
    name = settings.embedding_provider.lower()

    def factory() -> EmbeddingProvider:
        if name in {"huggingface", "hf", "sentence-transformers", "local"}:
            return HuggingFaceEmbeddingProvider(settings)
        if name in {"bedrock", "openai"}:
            raise NotImplementedError(f"Provider '{name}' reserved for future use")
        raise ValueError(f"Unknown embedding provider: {name}")

    return EmbeddingProviderSingleton.get(name, factory)
