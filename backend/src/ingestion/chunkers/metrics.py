from config.logging import get_logger
from config.settings import Settings
from config.token_utils import count_tokens, get_token_encoder
from domain.models import ChunkRecord, SectionNode
from ingestion.chunkers.hierarchical import HierarchicalChunker

logger = get_logger(__name__)


def log_chunk_metrics(
    *,
    source_key: str,
    total_pages: int,
    section_count: int,
    section_token_stats: dict[str, float],
    chunks: list[ChunkRecord],
) -> None:
    encoder = get_token_encoder()
    chunk_tokens = [count_tokens(chunk.content, encoder) for chunk in chunks]
    logger.info(
        "chunk_metrics",
        source_key=source_key,
        pages=total_pages,
        section_count=section_count,
        avg_section_tokens=section_token_stats.get("avg", 0),
        max_section_tokens=section_token_stats.get("max", 0),
        chunk_count=len(chunks),
        avg_chunk_tokens=round(sum(chunk_tokens) / len(chunk_tokens), 1) if chunk_tokens else 0,
        min_chunk_tokens=min(chunk_tokens) if chunk_tokens else 0,
        max_chunk_tokens=max(chunk_tokens) if chunk_tokens else 0,
    )


def section_token_stats(sections: list[SectionNode], settings: Settings) -> dict[str, float]:
    encoder = get_token_encoder()
    chunker = HierarchicalChunker(settings)
    tokens: list[int] = []
    for leaf in chunker.iter_leaves(sections):
        if leaf.content.strip():
            tokens.append(count_tokens(leaf.content, encoder))
    if not tokens:
        return {"avg": 0, "max": 0}
    return {"avg": round(sum(tokens) / len(tokens), 1), "max": max(tokens)}
