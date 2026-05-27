import re

from app.ingestion.domain.document import SectionNode

NAV_PATTERNS = [
    re.compile(r"^on this page\s*$", re.I),
    re.compile(r"^breadcrumb\s*$", re.I),
    re.compile(r"^table of contents\s*$", re.I),
    re.compile(r"^did this page help you\??\s*$", re.I),
]

HEADING_PATTERN = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)
CODE_FENCE_PATTERN = re.compile(r"```[\s\S]*?```", re.MULTILINE)


def mask_code_fences(text: str) -> tuple[str, list[str]]:
    blocks: list[str] = []

    def replacer(match: re.Match[str]) -> str:
        blocks.append(match.group(0))
        return f"__CODE_BLOCK_{len(blocks) - 1}__"

    masked = CODE_FENCE_PATTERN.sub(replacer, text)
    return masked, blocks


def unmask_code_fences(text: str, blocks: list[str]) -> str:
    for i, block in enumerate(blocks):
        text = text.replace(f"__CODE_BLOCK_{i}__", block)
    return text


def remove_nav_noise(text: str) -> str:
    lines = text.splitlines()
    cleaned: list[str] = []
    for line in lines:
        stripped = line.strip()
        if any(p.match(stripped) for p in NAV_PATTERNS):
            continue
        cleaned.append(line)
    return "\n".join(cleaned)


def normalize_whitespace(text: str) -> str:
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def dedupe_lines(text: str) -> str:
    seen: set[str] = set()
    result: list[str] = []
    for line in text.splitlines():
        key = line.strip().lower()
        if key and key in seen and len(key) < 80:
            continue
        if key:
            seen.add(key)
        result.append(line)
    return "\n".join(result)


def detect_sections(text: str) -> list[SectionNode]:
    """Build a flat list of sections from markdown headings."""
    sections: list[SectionNode] = []
    matches = list(HEADING_PATTERN.finditer(text))
    if not matches:
        return sections

    for i, match in enumerate(matches):
        level = len(match.group(1))
        title = match.group(2).strip()
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        content = text[start:end].strip()
        sections.append(SectionNode(title=title, level=level, content=content))
    return sections
