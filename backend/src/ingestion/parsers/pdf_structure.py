import re
import statistics
from dataclasses import dataclass

import fitz

from config.logging import get_logger
from domain.models import SectionNode
from ingestion.parsers.best_practices import parse_best_practice

logger = get_logger(__name__)

_BOLD_FLAG = 16
_MAX_FONT_SECTIONS = 120


@dataclass
class PdfStructure:
    document_title: str
    sections: list[SectionNode]
    text: str
    total_pages: int
    section_count: int


@dataclass
class _PdfLine:
    text: str
    page: int
    size: float
    bold: bool


def build_pdf_document_structure(pdf: fitz.Document) -> PdfStructure:
    """Build TOC-first hierarchy; font heuristics only when TOC is absent."""
    total_pages = len(pdf)
    document_title = _extract_document_title(pdf)
    toc = pdf.get_toc(simple=True) or []

    if toc:
        sections = _sections_from_toc(toc, pdf, total_pages)
        source = "toc"
    else:
        sections = _sections_from_fonts(pdf)
        source = "font"

    text = _extract_full_text(pdf)
    section_count = sum(1 for _ in _iter_leaves(sections))
    logger.info(
        "pdf_structure_built",
        source=source,
        document_title=document_title,
        total_pages=total_pages,
        top_level_sections=len(sections),
        leaf_sections=section_count,
    )
    return PdfStructure(
        document_title=document_title,
        sections=sections,
        text=text,
        total_pages=total_pages,
        section_count=section_count,
    )


def _extract_document_title(pdf: fitz.Document) -> str:
    meta = pdf.metadata or {}
    for key in ("title", "subject"):
        value = (meta.get(key) or "").strip()
        if value and value.lower() not in {"untitled", "microsoft word"}:
            return value

    toc = pdf.get_toc(simple=True) or []
    for item in toc:
        if len(item) >= 2 and int(item[0]) == 1:
            title = str(item[1]).strip()
            if title:
                return title

    return ""


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
        bp_id, bp_title = parse_best_practice(title)
        entries.append(
            {
                "level": level,
                "title": title,
                "page": page,
                "best_practice_id": bp_id,
                "best_practice_title": bp_title,
            }
        )

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
            best_practice_id=entry["best_practice_id"],
            best_practice_title=entry["best_practice_title"],
        )
        while stack and stack[-1].level >= node.level:
            stack.pop()
        if stack:
            stack[-1].children.append(node)
        else:
            roots.append(node)
        stack.append(node)

    _annotate_hierarchy_labels(roots)
    _fill_leaf_content(roots, pdf)
    return roots


def _annotate_hierarchy_labels(nodes: list[SectionNode], ancestors: list[SectionNode] | None = None) -> None:
    ancestors = ancestors or []
    for node in nodes:
        chain = ancestors + [node]
        if len(chain) >= 1:
            node.chapter = chain[0].title
        if len(chain) >= 2:
            node.section = chain[1].title
        if len(chain) >= 3:
            node.subsection = chain[2].title
        if node.children:
            _annotate_hierarchy_labels(node.children, chain)


def _sections_from_fonts(pdf: fitz.Document) -> list[SectionNode]:
    lines = _extract_lines(pdf)
    if not lines:
        return []

    subsections = _subsections_from_lines(lines)
    if len(subsections) > _MAX_FONT_SECTIONS:
        logger.warning(
            "font_heading_explosion",
            sections=len(subsections),
            action="collapse_to_single_document",
        )
        return [
            SectionNode(
                title="Document",
                level=1,
                content=_extract_full_text(pdf),
                page_start=1,
                page_end=len(pdf),
                chapter="Document",
            )
        ]

    if not subsections:
        return []

    if len(subsections) == 1:
        subsections[0].chapter = subsections[0].title
        return subsections

    root = SectionNode(
        title=subsections[0].title,
        level=1,
        page_start=subsections[0].page_start,
        page_end=subsections[-1].page_end,
        children=subsections,
        chapter=subsections[0].title,
    )
    _annotate_hierarchy_labels([root])
    return [root]


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
    size_to_level = {size: level + 1 for level, size in enumerate(heading_sizes[:4])}

    roots: list[SectionNode] = []
    stack: list[SectionNode] = []

    for line in lines:
        if _is_heading_line(line, body_size, toc_titles):
            level = size_to_level.get(line.size, min(len(size_to_level), 4))
            bp_id, bp_title = parse_best_practice(line.text)
            node = SectionNode(
                title=line.text,
                level=level,
                page_start=line.page,
                page_end=line.page,
                best_practice_id=bp_id,
                best_practice_title=bp_title,
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

    if not roots:
        return [
            SectionNode(
                title="Document",
                level=1,
                content="\n".join(line.text for line in lines),
                page_start=lines[0].page,
                page_end=lines[-1].page,
                chapter="Document",
            )
        ]
    _annotate_hierarchy_labels(roots)
    return roots


def _is_heading_line(line: _PdfLine, body_size: float, toc_titles: set[str]) -> bool:
    text = line.text.strip()
    if not text:
        return False
    if parse_best_practice(text)[0]:
        return True

    normalized = re.sub(r"\s+", " ", text).lower()
    if normalized in toc_titles:
        return True

    size_boost = line.size > body_size * 1.12
    bold_boost = line.bold and line.size >= body_size
    if not (size_boost or bold_boost):
        return False
    if len(text) > 120:
        return False
    if text.endswith(".") and len(text.split()) > 8:
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
