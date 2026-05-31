class ChunkExplosionError(Exception):
    """Raised when chunk count exceeds the configured document limit."""

    def __init__(self, chunk_count: int, limit: int, source_key: str = "") -> None:
        self.chunk_count = chunk_count
        self.limit = limit
        self.source_key = source_key
        detail = f"Unexpected chunk count: {chunk_count} (limit {limit})"
        if source_key:
            detail = f"{detail} for {source_key}"
        super().__init__(detail)
