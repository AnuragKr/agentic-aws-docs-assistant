from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

_BACKEND_ROOT = Path(__file__).resolve().parents[2]
_BACKEND_ENV_FILE = _BACKEND_ROOT / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_BACKEND_ENV_FILE if _BACKEND_ENV_FILE.is_file() else None,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = Field(default="agentic-aws-docs-assistant", alias="APP_NAME")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    aws_region: str = Field(default="us-east-1", alias="AWS_REGION")

    cloudwatch_logs_enabled: bool = Field(default=False, alias="CLOUDWATCH_LOGS_ENABLED")
    cloudwatch_log_group: str = Field(default="", alias="CLOUDWATCH_LOG_GROUP")
    cloudwatch_log_stream: str = Field(default="", alias="CLOUDWATCH_LOG_STREAM")

    s3_raw_bucket: str = Field(default="", alias="S3_BUCKET")
    s3_processed_bucket: str = Field(default="", alias="S3_PROCESSED_BUCKET")
    s3_processed_prefix: str = Field(default="processed/", alias="S3_PROCESSED_PREFIX")

    dynamodb_registry_table: str = Field(
        default="document-registry",
        alias="DYNAMODB_REGISTRY_TABLE",
    )

    docs_base_url: str = Field(
        default="https://docs.aws.amazon.com",
        alias="DOCS_BASE_URL",
    )

    # Sentence-aware chunks: 500–1200 tokens, 800 target, 100 overlap (tiktoken)
    chunk_min_tokens: int = Field(default=500, alias="CHUNK_MIN_TOKENS")
    chunk_max_tokens: int = Field(default=1200, alias="CHUNK_MAX_TOKENS")
    chunk_target_tokens: int = Field(default=800, alias="CHUNK_TARGET_TOKENS")
    chunk_overlap_tokens: int = Field(default=100, alias="CHUNK_OVERLAP_TOKENS")
    chunk_max_split_depth: int = Field(default=3, alias="CHUNK_MAX_SPLIT_DEPTH")
    chunk_max_chunks_per_document: int = Field(default=500, alias="CHUNK_MAX_CHUNKS_PER_DOCUMENT")

    embedding_provider: str = Field(default="huggingface", alias="EMBEDDING_PROVIDER")
    embedding_model_id: str = Field(
        default="sentence-transformers/all-MiniLM-L6-v2",
        alias="EMBEDDING_MODEL_ID",
    )
    embedding_dimension: int = Field(default=384, alias="EMBEDDING_DIMENSION")
    embedding_batch_size: int = Field(default=32, alias="EMBEDDING_BATCH_SIZE")
    ingestion_max_workers: int = Field(default=1, alias="INGESTION_MAX_WORKERS")

    opensearch_host: str = Field(default="localhost", alias="OPENSEARCH_HOST")
    opensearch_port: int = Field(default=9200, alias="OPENSEARCH_PORT")
    opensearch_index: str = Field(default="aws-docs", alias="OPENSEARCH_INDEX")
    opensearch_auth_mode: str = Field(default="basic", alias="OPENSEARCH_AUTH_MODE")
    opensearch_user: str = Field(default="admin", alias="OPENSEARCH_USER")
    opensearch_password: str = Field(default="", alias="OPENSEARCH_PASSWORD")
    opensearch_use_ssl: bool = Field(default=False, alias="OPENSEARCH_USE_SSL")
    opensearch_timeout: int = Field(default=60, alias="OPENSEARCH_TIMEOUT")
    opensearch_bulk_batch_size: int = Field(default=50, alias="OPENSEARCH_BULK_BATCH_SIZE")

    search_vector_k: int = Field(default=25, alias="SEARCH_VECTOR_K")
    search_rerank_candidates: int = Field(default=10, alias="SEARCH_RERANK_CANDIDATES")
    reranker_model_id: str = Field(default="BAAI/bge-reranker-base", alias="RERANKER_MODEL_ID")
    reranker_enabled: bool = Field(default=True, alias="RERANKER_ENABLED")
    warmup_models_on_startup: bool = Field(default=True, alias="WARMUP_MODELS_ON_STARTUP")
    search_timeout: int = Field(default=30, alias="SEARCH_TIMEOUT")
    health_opensearch_timeout: int = Field(default=5, alias="HEALTH_OPENSEARCH_TIMEOUT")

    cors_origins: str = Field(
        default="http://localhost:8501,http://127.0.0.1:8501",
        alias="CORS_ORIGINS",
    )

    retry_max_attempts: int = Field(default=3, alias="RETRY_MAX_ATTEMPTS")
    retry_min_wait: int = Field(default=1, alias="RETRY_MIN_WAIT")
    retry_max_wait: int = Field(default=10, alias="RETRY_MAX_WAIT")

    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
