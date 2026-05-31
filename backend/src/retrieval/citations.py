from domain.models import RetrievedChunk


def build_citation(chunk: RetrievedChunk) -> str:
    """Human-readable citation for search results."""
    parts = [p for p in [chunk.title, chunk.section, chunk.subsection] if p]
    heading = " > ".join(parts) if parts else chunk.document_id
    if chunk.source_url:
        return f"{heading} ({chunk.source_url})"
    return heading


def attach_citations(chunks: list[RetrievedChunk]) -> list[RetrievedChunk]:
    return [chunk.model_copy(update={"citation": build_citation(chunk)}) for chunk in chunks]
