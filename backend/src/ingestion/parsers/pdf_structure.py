import re
import statistics
from dataclasses import dataclass

import fitz

from config.logging import get_logger
from domain.models import SectionNode

logger = get_logger(__name__)

_BOLD_FLAG = 16


@dataclass
class _PdfLine:
    text: str
    page: int
    size: float
    bold: bool


def build_pdf_document_structure(pdf: fitz.Document) -> tuple[list[SectionNode], str, int]:
    """Build section tree from TOC (preferred) or font/bold heuristics."""
    total_pages = len(pdf)
    toc = pdf.get_toc(simple=True) or []

    if toc:
        sections = _sections_from_toc(toc, pdf, total_pages)
        source = "toc"
    else:
        sections = _sections_from_fonts(pdf)
        source = "font"

    text = _extract_full_text(pdf)
    logger.info(
        "pdf_structure_built",
        source=source,
        total_pages=total_pages,
        top_level_sections=len(sections),
    )
    return sections, text, total_pages


def _sections_from_toc(
    toc: list,
    pdf: fitz.Document,
    total_pages: int,
) -> list[SectionNode]:
    entries: list[dict] = []
    for item in toc:
        if len(item) < 3:
            continue
        level, title, page = int(item[0]), str(item[1]).strip(), int(item[2])
        if not title or page < 1:
            continue
        entries.append({"level": level, "title": title, "page": page})

    if not entries:
        return _sections_from_fonts(pdf)

    for index, entry in enumerate(entries):
        page_end = total_pages
        for next_entry in entries[index + 1 :]:
            if next_entry["level"] <= entry["level"]:
                page_end = max(entry["page"], next_entry["page"] - 1)
                break
        entry["page_end"] = page_end

    roots: list[SectionNode] = []
    stack: list[SectionNode] = []

    for entry in entries:
        node = SectionNode(
            title=entry["title"],
            level=entry["level"],
            page_start=entry["page"],
            page_end=entry["page_end"],
        )
        while stack and stack[-1].level >= node.level:
            stack.pop()
        if stack:
            stack[-1].children.append(node)
        else:
            roots.append(node)
        stack.append(node)

    _fill_leaf_content(roots, pdf)
    _enhance_with_font_headings(roots, pdf)
    return roots


def _enhance_with_font_headings(roots: list[SectionNode], pdf: fitz.Document) -> None:
    """Split large leaf sections using font/bold headings when content is very long."""
    for node in _iter_leaves(roots):
        if not node.content or node.page_start is None:
            continue
        if len(node.content.split()) < 800:
            continue

        page_lines = _lines_for_page_range(pdf, node.page_start, node.page_end)
        subsections = _subsections_from_lines(page_lines, toc_titles={node.title})
        if len(subsections) <= 1:
            continue

        node.children = subsections
        node.content = ""


def _sections_from_fonts(pdf: fitz.Document) -> list[SectionNode]:
    lines = _extract_lines(pdf)
    if not lines:
        return []

    subsections = _subsections_from_lines(lines)
    if not subsections:
        return []

    if len(subsections) == 1:
        return subsections

    return [
        SectionNode(
            title=subsections[0].title,
            level=1,
            page_start=subsections[0].page_start,
            page_end=subsections[-1].page_end,
            children=subsections,
        )
    ]


def _subsections_from_lines(
    lines: list[_PdfLine],
    toc_titles: set[str] | None = None,
) -> list[SectionNode]:
    if not lines:
        return []

    sizes = [line.size for line in lines]
    body_size = statistics.median(sizes)
    toc_titles = {t.lower() for t in (toc_titles or set())}

    heading_sizes = sorted(
        {line.size for line in lines if _is_heading_line(line, body_size, toc_titles)},
        reverse=True,
    )
    size_to_level = {size: level + 1 for level, size in enumerate(heading_sizes[:6])}

    roots: list[SectionNode] = []
    stack: list[SectionNode] = []

    for line in lines:
        if _is_heading_line(line, body_size, toc_titles):
            level = size_to_level.get(line.size, min(len(size_to_level), 6))
            node = SectionNode(
                title=line.text,
                level=level,
                page_start=line.page,
                page_end=line.page,
            )
            while stack and stack[-1].level >= node.level:
                stack.pop()
            if stack:
                stack[-1].children.append(node)
            else:
                roots.append(node)
            stack.append(node)
            continue

        if stack:
            current = stack[-1]
            current.content = (
                f"{current.content}\n{line.text}".strip() if current.content else line.text
            )
            if current.page_end is None or line.page > current.page_end:
                current.page_end = line.page

    return roots if roots else [
        SectionNode(
            title="Document",
            level=1,
            content="\n".join(line.text for line in lines),
            page_start=lines[0].page,
            page_end=lines[-1].page,
        )
    ]


def _is_heading_line(line: _PdfLine, body_size: float, toc_titles: set[str]) -> bool:
    text = line.text.strip()
    if not text:
        return False

    normalized = re.sub(r"\s+", " ", text).lower()
    if normalized in toc_titles:
        return True

    size_boost = line.size > body_size * 1.08
    bold_boost = line.bold and line.size >= body_size * 0.95
    if not (size_boost or bold_boost):
        return False
    if len(text) > 180:
        return False
    if text.endswith(".") and len(text.split()) > 10:
        return False
    return True


def _fill_leaf_content(sections: list[SectionNode], pdf: fitz.Document) -> None:
    for node in _iter_leaves(sections):
        if node.page_start is None:
            continue
        page_end = node.page_end or node.page_start
        node.content = _text_for_page_range(pdf, node.page_start, page_end)


def _iter_leaves(nodes: list[SectionNode]):
    for node in nodes:
        if node.children:
            yield from _iter_leaves(node.children)
        else:
            yield node


def _text_for_page_range(pdf: fitz.Document, page_start: int, page_end: int) -> str:
    parts: list[str] = []
    for page_num in range(page_start, min(page_end + 1, len(pdf) + 1)):
        text = pdf[page_num - 1].get_text("text").strip()
        if text:
            parts.append(text)
    return "\n\n".join(parts)


def _lines_for_page_range(
    pdf: fitz.Document,
    page_start: int,
    page_end: int | None,
) -> list[_PdfLine]:
    end = page_end or page_start
    lines: list[_PdfLine] = []
    for page_num in range(page_start, min(end + 1, len(pdf) + 1)):
        lines.extend(_lines_from_page(pdf[page_num - 1], page_num))
    return lines


def _extract_lines(pdf: fitz.Document) -> list[_PdfLine]:
    lines: list[_PdfLine] = []
    for page_num, page in enumerate(pdf, start=1):
        lines.extend(_lines_from_page(page, page_num))
    return lines


def _lines_from_page(page: fitz.Page, page_num: int) -> list[_PdfLine]:
    page_lines: list[_PdfLine] = []
    for block in page.get_text("dict").get("blocks", []):
        if block.get("type") != 0:
            continue
        for line in block.get("lines", []):
            spans = line.get("spans", [])
            if not spans:
                continue
            text = "".join(span["text"] for span in spans).strip()
            if not text:
                continue
            size = max(span["size"] for span in spans)
            bold = any(bool(span.get("flags", 0) & _BOLD_FLAG) for span in spans)
            page_lines.append(_PdfLine(text=text, page=page_num, size=size, bold=bold))
    return page_lines


def _extract_full_text(pdf: fitz.Document) -> str:
    parts: list[str] = []
    for page in pdf:
        text = page.get_text("text").strip()
        if text:
            parts.append(text)
    return "\n\n".join(parts)
