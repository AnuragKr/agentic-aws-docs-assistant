"""Sentence-boundary splitting for retrieval-quality chunks."""

import re

from config.token_utils import count_tokens

# End of sentence when followed by whitespace and a new thought (capital, digit, quote, paren).
_SENTENCE_BREAK_RE = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9\"'(])")
_CODE_FENCE_RE = re.compile(r"```[\s\S]*?```", re.MULTILINE)
_LIST_ITEM_RE = re.compile(r"^[\s]*(?:[-*•]|\d+[.)])\s+", re.MULTILINE)


def split_into_sentences(text: str) -> list[str]:
    """Split text into atomic units that are never broken across chunks."""
    text = text.strip()
    if not text:
        return []

    protected: list[str] = []

    def _protect(match: re.Match[str]) -> str:
        protected.append(match.group(0))
        return f"__CODE_BLOCK_{len(protected) - 1}__"

    working = _CODE_FENCE_RE.sub(_protect, text)
    sentences: list[str] = []

    for block in re.split(r"\n\n+", working):
        block = block.strip()
        if not block:
            continue

        if block.startswith("__CODE_BLOCK_"):
            sentences.append(_restore(block, protected))
            continue

        if _LIST_ITEM_RE.search(block):
            for line in block.splitlines():
                line = line.strip()
                if line:
                    sentences.append(_restore(line, protected))
            continue

        if "\n" in block and not _SENTENCE_BREAK_RE.search(block):
            for line in block.splitlines():
                line = line.strip()
                if line:
                    sentences.append(_restore(line, protected))
            continue

        parts = _SENTENCE_BREAK_RE.split(block) or [block]

        for part in parts:
            part = part.strip()
            if part:
                sentences.append(_restore(part, protected))

    return sentences


def join_sentences(sentences: list[str]) -> str:
    if not sentences:
        return ""
    if len(sentences) == 1:
        return sentences[0]
    return " ".join(sentences)


def build_sentence_chunks(
    text: str,
    *,
    target_tokens: int,
    min_tokens: int,
    max_tokens: int,
    overlap_tokens: int,
    encoder,
) -> list[str]:
    """
    Accumulate complete sentences into chunks.

    - Sections at or below max_tokens stay as one chunk.
    - Targets ~target_tokens per chunk without splitting sentences.
    - Overlap reuses trailing full sentences only.
    """
    sentences = split_into_sentences(text)
    if not sentences:
        return []

    def tokens(parts: list[str]) -> int:
        return count_tokens(join_sentences(parts), encoder)

    if tokens(sentences) <= max_tokens:
        return [join_sentences(sentences)]

    chunks: list[str] = []
    start = 0

    while start < len(sentences):
        chunk_parts: list[str] = []
        index = start

        while index < len(sentences):
            sentence = sentences[index]
            sentence_tokens = count_tokens(sentence, encoder)

            if sentence_tokens > max_tokens:
                if chunk_parts:
                    break
                chunk_parts = [sentence]
                index += 1
                break

            candidate = chunk_parts + [sentence]
            candidate_tokens = tokens(candidate)

            if not chunk_parts:
                chunk_parts.append(sentence)
                index += 1
                continue

            if candidate_tokens > max_tokens:
                break

            if candidate_tokens <= target_tokens:
                chunk_parts.append(sentence)
                index += 1
                continue

            if tokens(chunk_parts) < min_tokens:
                chunk_parts.append(sentence)
                index += 1
                continue

            break

        if not chunk_parts:
            chunk_parts = [sentences[start]]
            index = start + 1

        chunks.append(join_sentences(chunk_parts))

        if index >= len(sentences):
            break

        overlap_parts = _overlap_sentences(chunk_parts, overlap_tokens, encoder)
        if overlap_parts:
            overlap_start = len(chunk_parts) - len(overlap_parts)
            next_start = start + overlap_start
            if next_start <= start:
                next_start = index
        else:
            next_start = index

        start = next_start

    return _merge_trailing_small(chunks, min_tokens, max_tokens, encoder)


def _overlap_sentences(
    chunk_parts: list[str],
    overlap_tokens: int,
    encoder,
) -> list[str]:
    if overlap_tokens <= 0 or not chunk_parts:
        return []

    selected: list[str] = []
    total = 0
    for sentence in reversed(chunk_parts):
        sentence_tokens = count_tokens(sentence, encoder)
        if selected and total + sentence_tokens > overlap_tokens:
            break
        selected.insert(0, sentence)
        total += sentence_tokens
        if total >= overlap_tokens:
            break
    return selected


def _merge_trailing_small(
    chunks: list[str],
    min_tokens: int,
    max_tokens: int,
    encoder,
) -> list[str]:
    if len(chunks) < 2:
        return chunks

    last_tokens = count_tokens(chunks[-1], encoder)
    if last_tokens >= min_tokens:
        return chunks

    combined = f"{chunks[-2]} {chunks[-1]}".strip()
    if count_tokens(combined, encoder) <= max_tokens:
        return [*chunks[:-2], combined]
    return chunks


def _restore(text: str, protected: list[str]) -> str:
    for index, block in enumerate(protected):
        text = text.replace(f"__CODE_BLOCK_{index}__", block)
    return text
