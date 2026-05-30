from config.logging import get_logger
from domain.models import SectionNode

logger = get_logger(__name__)


def extract_hierarchy_from_docling(doc) -> list[SectionNode]:
    """Build section tree from Docling document structure (not regex)."""
    sections: list[SectionNode] = []
    stack: list[SectionNode] = []

    try:
        items = list(doc.iterate_items())
    except Exception:
        logger.warning("docling_iterate_failed", reason="falling_back_to_empty_sections")
        return []

    for item, level in items:
        label = str(getattr(item, "label", "")).lower()
        text = (getattr(item, "text", "") or "").strip()
        if not text:
            continue

        is_heading = "section_header" in label or label in {"title", "heading"}
        if is_heading:
            heading_level = getattr(item, "level", None) or level or len(stack) + 1
            node = SectionNode(title=text, level=int(heading_level), content="")
            while stack and stack[-1].level >= node.level:
                stack.pop()
            if stack:
                stack[-1].children.append(node)
            else:
                sections.append(node)
            stack.append(node)
        elif stack:
            node = stack[-1]
            node.content = f"{node.content}\n\n{text}".strip() if node.content else text

    logger.info("docling_hierarchy_extracted", section_count=len(sections))
    return sections
