import re

_BP_ID_RE = re.compile(
    r"\b((?:SEC|OPS|REL|PER|COST|SUS|ARCH|GOV|DATA)\d{2}-BP\d{2})\b",
    re.I,
)


def parse_best_practice(title: str) -> tuple[str | None, str | None]:
    """Extract Well-Architected best practice id and title from a TOC heading."""
    match = _BP_ID_RE.search(title.strip())
    if not match:
        return None, None
    bp_id = match.group(1).upper()
    remainder = title[match.end() :].strip(" :-–—")
    return bp_id, remainder or None


def path_label(title: str, best_practice_id: str | None) -> str:
    return best_practice_id or title.strip()
