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

    s3_raw_bucket: str = Field(default="", alias="S3_BUCKET")
    s3_raw_prefix: str = Field(default="", alias="S3_PREFIX")
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

    # 800–1200 tokens target, 100–150 overlap (tiktoken)
    chunk_max_tokens: int = Field(default=1000, alias="CHUNK_MAX_TOKENS")
    chunk_overlap_tokens: int = Field(default=125, alias="CHUNK_OVERLAP_TOKENS")

    embedding_provider: str = Field(default="huggingface", alias="EMBEDDING_PROVIDER")
    embedding_model_id: str = Field(
        default="sentence-transformers/all-MiniLM-L6-v2",
        alias="EMBEDDING_MODEL_ID",
    )
    embedding_batch_size: int = Field(default=32, alias="EMBEDDING_BATCH_SIZE")

    opensearch_host: str = Field(default="localhost", alias="OPENSEARCH_HOST")
    opensearch_port: int = Field(default=9200, alias="OPENSEARCH_PORT")
    opensearch_index: str = Field(default="aws-docs", alias="OPENSEARCH_INDEX")
    opensearch_auth_mode: str = Field(default="basic", alias="OPENSEARCH_AUTH_MODE")
    opensearch_user: str = Field(default="admin", alias="OPENSEARCH_USER")
    opensearch_password: str = Field(default="", alias="OPENSEARCH_PASSWORD")
    opensearch_use_ssl: bool = Field(default=False, alias="OPENSEARCH_USE_SSL")

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
