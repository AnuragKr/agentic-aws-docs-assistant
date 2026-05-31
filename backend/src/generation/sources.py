from generation.models import SourceReference


def deduplicate_sources(sources: list[SourceReference]) -> list[SourceReference]:
    """Keep unique sources by document name and section."""
    seen: set[tuple[str, str | None]] = set()
    unique: list[SourceReference] = []
    for source in sources:
        section = source.section_title or None
        key = (source.document_name, section)
        if key in seen:
            continue
        seen.add(key)
        unique.append(source)
    return unique


def format_source_label(source: SourceReference | dict) -> str:
    """Render a source for UI display — omit blank page numbers."""
    if isinstance(source, SourceReference):
        document_name = source.document_name
        section_title = source.section_title
        page_number = source.page_number
    else:
        document_name = source.get("document_name", "Document")
        section_title = source.get("section_title")
        page_number = source.get("page_number")

    parts = [document_name]
    if section_title:
        parts.append(section_title)
    if page_number is not None:
        parts.append(f"Page {page_number}")
    return " | ".join(parts)
