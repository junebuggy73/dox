"""Split markdown content into token-bounded chunks at section boundaries."""

from __future__ import annotations

import re


def estimate_tokens(text: str) -> int:
    """Rough token estimate: ~4 characters per token for English/code markdown."""
    return len(text) // 4


def _heading_level(line: str) -> int | None:
    """Return heading level (1-6) if line is a markdown heading, else None."""
    m = re.match(r"^(#{1,6})\s", line)
    return len(m.group(1)) if m else None


def chunk(text: str, max_tokens: int) -> list[dict]:
    """Split markdown into chunks that respect section boundaries.

    Strategy:
    1. Split text into sections at heading boundaries.
    2. Greedily pack sections into chunks up to max_tokens.
    3. If a single section exceeds max_tokens, split it at paragraph
       boundaries (blank lines). If a paragraph still exceeds, hard-split
       by line count.

    Returns list of dicts: {chunk: int, total_chunks: int, tokens: int, content: str}
    """
    sections = _split_at_headings(text)
    chunks: list[str] = []
    current: list[str] = []
    current_tokens = 0

    for section in sections:
        section_tokens = estimate_tokens(section)

        # Section fits in current chunk
        if current_tokens + section_tokens <= max_tokens:
            current.append(section)
            current_tokens += section_tokens
            continue

        # Flush current chunk if non-empty
        if current:
            chunks.append("\n\n".join(current))
            current = []
            current_tokens = 0

        # Section fits in a fresh chunk
        if section_tokens <= max_tokens:
            current.append(section)
            current_tokens = section_tokens
            continue

        # Section is too large — split at paragraph boundaries
        for sub in _split_large_section(section, max_tokens):
            sub_tokens = estimate_tokens(sub)
            if current_tokens + sub_tokens <= max_tokens:
                current.append(sub)
                current_tokens += sub_tokens
            else:
                if current:
                    chunks.append("\n\n".join(current))
                current = [sub]
                current_tokens = sub_tokens

    if current:
        chunks.append("\n\n".join(current))

    total = len(chunks)
    return [
        {
            "chunk": i + 1,
            "total_chunks": total,
            "tokens": estimate_tokens(c),
            "content": c,
        }
        for i, c in enumerate(chunks)
    ]


def _split_at_headings(text: str) -> list[str]:
    """Split markdown into sections at heading boundaries."""
    lines = text.split("\n")
    sections: list[str] = []
    current: list[str] = []

    for line in lines:
        if _heading_level(line) is not None and current:
            sections.append("\n".join(current))
            current = []
        current.append(line)

    if current:
        sections.append("\n".join(current))

    return sections


def _split_large_section(section: str, max_tokens: int) -> list[str]:
    """Split an oversized section at paragraph boundaries (blank lines)."""
    paragraphs = re.split(r"\n\n+", section)
    result: list[str] = []
    current: list[str] = []
    current_tokens = 0

    for para in paragraphs:
        para_tokens = estimate_tokens(para)

        if para_tokens > max_tokens:
            # Paragraph itself is too large — hard split by lines
            if current:
                result.append("\n\n".join(current))
                current = []
                current_tokens = 0
            for hard_chunk in _hard_split(para, max_tokens):
                result.append(hard_chunk)
            continue

        if current_tokens + para_tokens <= max_tokens:
            current.append(para)
            current_tokens += para_tokens
        else:
            if current:
                result.append("\n\n".join(current))
            current = [para]
            current_tokens = para_tokens

    if current:
        result.append("\n\n".join(current))

    return result


def _hard_split(text: str, max_tokens: int) -> list[str]:
    """Last resort: split text by lines to fit within token budget."""
    lines = text.split("\n")
    chunks: list[str] = []
    current: list[str] = []
    current_tokens = 0

    for line in lines:
        line_tokens = estimate_tokens(line) + 1  # +1 for newline
        if current_tokens + line_tokens > max_tokens and current:
            chunks.append("\n".join(current))
            current = []
            current_tokens = 0
        current.append(line)
        current_tokens += line_tokens

    if current:
        chunks.append("\n".join(current))

    return chunks
