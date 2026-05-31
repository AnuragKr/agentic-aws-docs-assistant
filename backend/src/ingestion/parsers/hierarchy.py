import re
import statistics

from config.logging import get_logger
from domain.models import SectionNode

logger = get_logger(__name__)

MARKDOWN_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)
NUMBERED_HEADING_RE = re.compile(r"^(\d+(?:\.\d+)*)\s+([A-Z][\w\s\-,.]+)$", re.MULTILINE)


def extract_hierarchy_from_text(text: str) -> list[SectionNode]:
    """Build section tree from markdown-style or numbered headings in plain text."""
    markdown_matches = list(MARKDOWN_HEADING_RE.finditer(text))
    if markdown_matches:
        sections = _sections_from_markdown(text, markdown_matches)
        logger.info("headings_extracted", source="markdown", section_count=len(sections))
        return sections

    numbered_matches = list(NUMBERED_HEADING_RE.finditer(text))
    if numbered_matches:
        sections = _sections_from_numbered(text, numbered_matches)
        logger.info("headings_extracted", source="numbered", section_count=len(sections))
        return sections

    logger.info("headings_extracted", source="none", section_count=0)
    return []


def extract_hierarchy_from_html(soup) -> list[SectionNode]:
    """Build section tree from HTML h1–h6 tags."""
    sections: list[SectionNode] = []
    stack: list[SectionNode] = []

    for tag in soup.find_all(re.compile(r"^h[1-6]$", re.I)):
        level = int(tag.name[1])
        title = tag.get_text(" ", strip=True)
        if not title:
            continue

        content_parts: list[str] = []
        for sibling in tag.next_siblings:
            if getattr(sibling, "name", None) and re.match(r"^h[1-6]$", sibling.name, re.I):
                break
            chunk = (
                sibling.get_text(" ", strip=True)
                if hasattr(sibling, "get_text")
                else str(sibling).strip()
            )
            if chunk:
                content_parts.append(chunk)

        _insert_section(
            sections,
            stack,
            SectionNode(title=title, level=level, content="\n\n".join(content_parts)),
        )

    logger.info("headings_extracted", source="html", section_count=len(sections))
    return sections


def extract_hierarchy_from_pdf_lines(lines: list[tuple[str, float]]) -> list[SectionNode]:
    """Build section tree from PDF lines tagged with font size (PyMuPDF)."""
    if not lines:
        return []

    sizes = [size for _, size in lines]
    body_size = statistics.median(sizes)
    heading_sizes = sorted(
        {size for text, size in lines if _is_pdf_heading(text, size, body_size)},
        reverse=True,
    )
    if not heading_sizes:
        return []

    size_to_level = {size: level + 1 for level, size in enumerate(heading_sizes[:6])}

    sections: list[SectionNode] = []
    stack: list[SectionNode] = []

    for text, size in lines:
        if not _is_pdf_heading(text, size, body_size):
            if stack:
                node = stack[-1]
                node.content = f"{node.content}\n{text}".strip() if node.content else text
            continue

        level = size_to_level.get(size, min(len(size_to_level), 6))
        _insert_section(sections, stack, SectionNode(title=text, level=level, content=""))

    logger.info("headings_extracted", source="pdf_font", section_count=len(sections))
    return sections


def _is_pdf_heading(text: str, size: float, body_size: float) -> bool:
    if size <= body_size * 1.08:
        return False
    if len(text) > 180:
        return False
    if text.endswith(".") and len(text.split()) > 8:
        return False
    return True


def _sections_from_markdown(text: str, matches: list[re.Match]) -> list[SectionNode]:
    sections: list[SectionNode] = []
    stack: list[SectionNode] = []

    for index, match in enumerate(matches):
        level = len(match.group(1))
        title = match.group(2).strip()
        content_start = match.end()
        content_end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        content = text[content_start:content_end].strip()
        _insert_section(sections, stack, SectionNode(title=title, level=level, content=content))

    return sections


def _sections_from_numbered(text: str, matches: list[re.Match]) -> list[SectionNode]:
    sections: list[SectionNode] = []
    stack: list[SectionNode] = []

    for index, match in enumerate(matches):
        number = match.group(1)
        title = match.group(2).strip()
        level = number.count(".") + 1
        content_start = match.end()
        content_end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        content = text[content_start:content_end].strip()
        _insert_section(
            sections,
            stack,
            SectionNode(title=f"{number} {title}", level=level, content=content),
        )

    return sections


def _insert_section(
    sections: list[SectionNode],
    stack: list[SectionNode],
    node: SectionNode,
) -> None:
    while stack and stack[-1].level >= node.level:
        stack.pop()
    if stack:
        stack[-1].children.append(node)
    else:
        sections.append(node)
    stack.append(node)
