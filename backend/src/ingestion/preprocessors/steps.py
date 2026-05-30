import re

NAV_LINE_RE = re.compile(r"^(home|navigation|breadcrumb|menu|skip to)\b", re.I)
WHITESPACE_RE = re.compile(r"[ \t]+")
MULTI_NEWLINE_RE = re.compile(r"\n{3,}")
LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")


def remove_navigation(text: str) -> str:
    lines = [ln for ln in text.splitlines() if not NAV_LINE_RE.match(ln.strip())]
    return "\n".join(lines)


def remove_headers_footers(text: str) -> str:
    lines = text.splitlines()
    if len(lines) <= 6:
        return text
    return "\n".join(lines[1:-1])


def normalize_whitespace(text: str) -> str:
    text = WHITESPACE_RE.sub(" ", text)
    return MULTI_NEWLINE_RE.sub("\n\n", text).strip()


def preserve_links(text: str) -> str:
    return LINK_RE.sub(r"\1 (\2)", text)
