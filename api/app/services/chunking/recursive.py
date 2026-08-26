"""
Shared recursive splitting utilities.

Other squad members can reuse ``recursive_split`` from PDF/PPT/image chunkers.
"""

from __future__ import annotations

import re

PLACEHOLDER_PREFIX = "\x00BLOCK"
PLACEHOLDER_SUFFIX = "\x00"

FENCED_CODE_PATTERN = re.compile(r"```[^\n]*\n.*?```", re.DOTALL)
SENTENCE_PATTERN = re.compile(r"(?<=[.!?])\s+(?=\S)")
LIST_ITEM_PATTERN = re.compile(r"^\s*(?:[-*+]|\d+\.)\s+")
TABLE_SEPARATOR_PATTERN = re.compile(r"^\|\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)+\|?\s*$")


def approximate_token_count(text: str) -> int:
    """Estimate token count using words * 1.3 heuristic."""
    if not text or not text.strip():
        return 0
    return max(1, int(len(text.split()) * 1.3))


def is_table_line(line: str) -> bool:
    stripped = line.strip()
    return stripped.startswith("|") and stripped.endswith("|")


def _join_units(units: list[str]) -> str:
    return "\n\n".join(part.strip() for part in units if part.strip())


def _is_table_separator(line: str) -> bool:
    return bool(TABLE_SEPARATOR_PATTERN.match(line.strip()))


def _extract_protected_blocks(text: str) -> tuple[str, dict[str, str]]:
    blocks: dict[str, str] = {}

    def _register_block(block_text: str) -> str:
        key = f"{PLACEHOLDER_PREFIX}{len(blocks)}{PLACEHOLDER_SUFFIX}"
        blocks[key] = block_text
        return key

    def _replace_code(match: re.Match[str]) -> str:
        return _register_block(match.group(0))

    masked = FENCED_CODE_PATTERN.sub(_replace_code, text)

    lines = masked.split("\n")
    output_lines: list[str] = []
    index = 0

    while index < len(lines):
        line = lines[index]
        if is_table_line(line):
            table_lines = [line]
            index += 1
            while index < len(lines) and is_table_line(lines[index]):
                table_lines.append(lines[index])
                index += 1
            output_lines.append(_register_block("\n".join(table_lines)))
            continue

        output_lines.append(line)
        index += 1

    return "\n".join(output_lines), blocks


def _restore_blocks(text: str, blocks: dict[str, str]) -> str:
    restored = text
    for placeholder, original in blocks.items():
        restored = restored.replace(placeholder, original)
    return restored


def _split_paragraphs(text: str) -> list[str]:
    parts = re.split(r"\n\s*\n", text)
    return [part.strip() for part in parts if part.strip()]


def _split_list_items(text: str) -> list[str]:
    lines = text.splitlines()
    if not lines:
        return []

    items: list[str] = []
    current: list[str] = []

    for line in lines:
        if LIST_ITEM_PATTERN.match(line):
            if current:
                items.append("\n".join(current).strip())
            current = [line]
        elif current:
            current.append(line)
        elif line.strip():
            return _split_paragraphs(text)

    if current:
        items.append("\n".join(current).strip())

    return items if len(items) > 1 else [text.strip()]


def _split_sentences(text: str) -> list[str]:
    parts = SENTENCE_PATTERN.split(text.strip())
    sentences = [part.strip() for part in parts if part.strip()]
    return sentences if sentences else [text.strip()]


def _split_words(text: str, chunk_size: int, overlap: int) -> list[str]:
    words = text.split()
    if not words:
        return []

    max_words = max(1, int(chunk_size / 1.3))
    overlap_words = max(0, int(overlap / 1.3))
    step = max(1, max_words - overlap_words)

    chunks: list[str] = []
    start = 0
    while start < len(words):
        end = min(len(words), start + max_words)
        chunks.append(" ".join(words[start:end]))
        if end >= len(words):
            break
        start += step

    return chunks


def _split_large_unit(text: str, chunk_size: int, overlap: int) -> list[str]:
    if approximate_token_count(text) <= chunk_size:
        return [text.strip()]

    paragraphs = _split_paragraphs(text)
    if len(paragraphs) > 1:
        return _flatten_splits(paragraphs, chunk_size, overlap)

    list_items = _split_list_items(text)
    if len(list_items) > 1:
        return _flatten_splits(list_items, chunk_size, overlap)

    sentences = _split_sentences(text)
    if len(sentences) > 1:
        return _flatten_splits(sentences, chunk_size, overlap)

    return _split_words(text, chunk_size, overlap)


def _flatten_splits(units: list[str], chunk_size: int, overlap: int) -> list[str]:
    result: list[str] = []
    for unit in units:
        if approximate_token_count(unit) <= chunk_size:
            result.append(unit.strip())
        else:
            result.extend(_split_large_unit(unit, chunk_size, overlap))
    return result


def _merge_with_overlap(units: list[str], chunk_size: int, overlap: int) -> list[str]:
    if not units:
        return []

    chunks: list[str] = []
    current_units: list[str] = []
    current_tokens = 0

    for unit in units:
        unit = unit.strip()
        if not unit:
            continue

        unit_tokens = approximate_token_count(unit)
        if unit_tokens > chunk_size:
            if current_units:
                chunks.append(_join_units(current_units))
                current_units = []
                current_tokens = 0
            chunks.extend(
                _merge_with_overlap(
                    _split_large_unit(unit, chunk_size, overlap),
                    chunk_size,
                    overlap,
                )
            )
            continue

        candidate_tokens = approximate_token_count(_join_units([*current_units, unit]))
        if current_units and candidate_tokens > chunk_size:
            chunks.append(_join_units(current_units))
            overlap_text = _take_overlap(chunks[-1], overlap)
            current_units = [overlap_text, unit] if overlap_text else [unit]
            current_tokens = approximate_token_count(_join_units(current_units))
        else:
            current_units.append(unit)
            current_tokens = candidate_tokens

    if current_units:
        chunks.append(_join_units(current_units))

    return [chunk for chunk in chunks if chunk.strip()]


def _take_overlap(text: str, overlap_tokens: int) -> str:
    if overlap_tokens <= 0:
        return ""
    words = text.split()
    overlap_words = max(1, int(overlap_tokens / 1.3))
    if len(words) <= overlap_words:
        return text
    return " ".join(words[-overlap_words:])


def recursive_split(text: str, chunk_size: int = 500, overlap: int = 100) -> list[str]:
    """
    Recursively split text using paragraph, sentence, then word boundaries.

    Code blocks and markdown tables remain intact. Adjacent chunks share
    approximately ``overlap`` tokens from the previous chunk tail.
    """
    cleaned = text.strip()
    if not cleaned:
        return []

    masked, blocks = _extract_protected_blocks(cleaned)

    if approximate_token_count(masked) <= chunk_size:
        return [_restore_blocks(masked, blocks)]

    units = _split_paragraphs(masked)
    if len(units) == 1:
        units = _split_large_unit(units[0], chunk_size, overlap)

    chunks = _merge_with_overlap(units, chunk_size, overlap)
    return [_restore_blocks(chunk, blocks) for chunk in chunks if chunk.strip()]
