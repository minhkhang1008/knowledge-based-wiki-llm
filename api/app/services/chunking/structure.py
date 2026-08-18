"""Structure-aware Markdown parsing shared by PDF and image chunkers."""

from __future__ import annotations

from dataclasses import dataclass, field
import re

from app.services.chunking.config import ChunkConfig
from app.services.chunking.recursive import approximate_token_count, recursive_split


HEADING_PATTERN = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
LIST_PATTERN = re.compile(r"^\s*(?:[-*+]\s+|\d+[.)]\s+)")
IMAGE_MARKDOWN_PATTERN = re.compile(r"^!\[([^]]*)]\(([^)]+)\)\s*$")
OCR_LABEL_PATTERN = re.compile(r"^>\s*\*\*(?:Nội dung .*ảnh|Nội dung nhận dạng từ ảnh):\*\*\s*$", re.IGNORECASE)
OCR_META_PATTERN = re.compile(
    r"^<!--\s*ocr-meta:\s*engine=([^;]+);\s*confidence=([0-9.]+);\s*regions=(\d+)"
    r"(?:;\s*bbox=([0-9.,-]+))?\s*-->$",
    re.IGNORECASE,
)


def _ocr_metadata(match: re.Match[str]) -> dict[str, str | int | float]:
    metadata: dict[str, str | int | float] = {
        "ocr_engine": match.group(1).strip(),
        "ocr_confidence": float(match.group(2)),
        "ocr_regions": int(match.group(3)),
    }
    if match.group(4):
        metadata["bbox"] = match.group(4)
    return metadata


@dataclass
class SemanticUnit:
    content: str
    block_type: str
    heading_path: tuple[str, ...] = ()
    metadata: dict[str, str | int | float | bool] = field(default_factory=dict)


def _is_table_line(line: str) -> bool:
    stripped = line.strip()
    return stripped.startswith("|") and stripped.endswith("|")


def _heading_prefix(path: tuple[str, ...]) -> str:
    return " > ".join(part for part in path if part)


def parse_markdown_units(markdown_text: str) -> list[SemanticUnit]:
    """Convert Markdown into headings, prose, lists, tables and image OCR units."""
    lines = markdown_text.splitlines()
    units: list[SemanticUnit] = []
    headings: list[str] = []
    buffer: list[str] = []
    buffer_type = "paragraph"

    def flush() -> None:
        nonlocal buffer, buffer_type
        content = "\n".join(buffer).strip()
        if content:
            units.append(SemanticUnit(content, buffer_type, tuple(headings)))
        buffer = []
        buffer_type = "paragraph"

    index = 0
    while index < len(lines):
        line = lines[index]
        stripped = line.strip()
        heading = HEADING_PATTERN.match(stripped)
        if heading:
            flush()
            level = len(heading.group(1))
            title = heading.group(2).strip()
            headings = headings[: level - 1]
            while len(headings) < level - 1:
                headings.append("")
            headings.append(title)
            index += 1
            continue

        if _is_table_line(line):
            flush()
            table_lines: list[str] = []
            while index < len(lines) and _is_table_line(lines[index]):
                table_lines.append(lines[index].strip())
                index += 1
            units.append(SemanticUnit("\n".join(table_lines), "table", tuple(headings)))
            continue

        if stripped == "<img>" or stripped.startswith("<img> "):
            flush()
            image_path = stripped[5:].strip()
            ocr_lines: list[str] = []
            ocr_metadata: dict[str, str | int | float] = {}
            index += 1
            if index < len(lines):
                meta_match = OCR_META_PATTERN.match(lines[index].strip())
                if meta_match:
                    ocr_metadata = _ocr_metadata(meta_match)
                    index += 1
            if index < len(lines) and lines[index].strip() == '"""':
                index += 1
                while index < len(lines) and lines[index].strip() != '"""':
                    ocr_lines.append(lines[index].strip())
                    index += 1
                if index < len(lines):
                    index += 1
            content = "\n".join(part for part in ocr_lines if part).strip()
            metadata: dict[str, str | int | float | bool] = {
                "indexable": bool(content),
                **ocr_metadata,
            }
            if image_path:
                metadata["image_path"] = image_path
            units.append(SemanticUnit(content, "image_ocr", tuple(headings), metadata))
            continue

        image_match = IMAGE_MARKDOWN_PATTERN.match(stripped)
        if image_match:
            flush()
            alt_text, image_path = image_match.groups()
            ocr_lines: list[str] = []
            ocr_metadata: dict[str, str | int | float] = {}
            index += 1
            while index < len(lines) and not lines[index].strip():
                index += 1
            if index < len(lines):
                meta_match = OCR_META_PATTERN.match(lines[index].strip())
                if meta_match:
                    ocr_metadata = _ocr_metadata(meta_match)
                    index += 1
            if index < len(lines) and OCR_LABEL_PATTERN.match(lines[index].strip()):
                index += 1
                while index < len(lines) and lines[index].lstrip().startswith(">"):
                    value = lines[index].lstrip()[1:].strip()
                    if value:
                        ocr_lines.append(value)
                    index += 1
            content = "\n".join(ocr_lines).strip()
            units.append(SemanticUnit(
                content,
                "image_ocr",
                tuple(headings),
                {
                    "image_path": image_path,
                    "image_alt": alt_text,
                    "indexable": bool(content),
                    **ocr_metadata,
                },
            ))
            continue

        if not stripped:
            flush()
            index += 1
            continue

        current_type = "list" if LIST_PATTERN.match(line) else "paragraph"
        if buffer and current_type != buffer_type:
            flush()
        buffer_type = current_type
        buffer.append(stripped)
        index += 1

    flush()
    return units


def _split_table(content: str, max_tokens: int) -> list[str]:
    lines = [line for line in content.splitlines() if line.strip()]
    if approximate_token_count(content) <= max_tokens or len(lines) <= 3:
        return [content]

    separator_cells = [cell.strip() for cell in lines[1].strip().strip("|").split("|")]
    has_separator = bool(separator_cells) and all(
        re.fullmatch(r":?-{3,}:?", cell) for cell in separator_cells
    )
    header_count = 2 if has_separator else 1
    header = lines[:header_count]
    rows = lines[header_count:]
    parts: list[str] = []
    current = list(header)
    for row in rows:
        candidate = "\n".join([*current, row])
        if len(current) > header_count and approximate_token_count(candidate) > max_tokens:
            parts.append("\n".join(current))
            current = [*header, row]
        else:
            current.append(row)
    if len(current) > header_count:
        parts.append("\n".join(current))
    return parts or [content]


def _unit_parts(unit: SemanticUnit, config: ChunkConfig) -> list[SemanticUnit]:
    if not unit.content.strip() or unit.metadata.get("indexable") is False:
        return []
    configured_max = config.image_chunk_size if unit.block_type == "image_ocr" else config.chunk_size
    # Heading được lặp ở mỗi chunk, nên trừ ngân sách prefix trước khi chia body.
    max_tokens = max(1, configured_max - approximate_token_count(_heading_prefix(unit.heading_path)))
    overlap = config.image_overlap if unit.block_type == "image_ocr" else config.overlap
    overlap = min(overlap, max(0, max_tokens // 3))
    if unit.block_type == "table":
        contents = _split_table(unit.content, max_tokens)
        overlap = 0
    elif approximate_token_count(unit.content) > max_tokens:
        contents = recursive_split(unit.content, max_tokens, overlap)
    else:
        contents = [unit.content]
    return [SemanticUnit(content, unit.block_type, unit.heading_path, dict(unit.metadata)) for content in contents]


def pack_semantic_units(units: list[SemanticUnit], config: ChunkConfig) -> list[dict]:
    """Pack related prose while keeping tables/images and heading boundaries intact."""
    expanded = [part for unit in units for part in _unit_parts(unit, config)]
    packed: list[dict] = []
    current: list[SemanticUnit] = []

    def flush() -> None:
        nonlocal current
        if not current:
            return
        heading_path = current[0].heading_path
        prefix = _heading_prefix(heading_path)
        body = "\n\n".join(unit.content.strip() for unit in current if unit.content.strip())
        content = f"{prefix}\n\n{body}" if prefix else body
        block_types = {unit.block_type for unit in current}
        metadata = dict(current[0].metadata)
        metadata.update({
            "block_type": next(iter(block_types)) if len(block_types) == 1 else "mixed",
            "heading_path": prefix,
        })
        packed.append({"content": content.strip(), "metadata": metadata})
        current = []

    for unit in expanded:
        atomic = unit.block_type in {"table", "image_ocr"}
        if atomic:
            flush()
            current = [unit]
            flush()
            continue
        same_heading = not current or current[0].heading_path == unit.heading_path
        candidate_body = "\n\n".join([*(item.content for item in current), unit.content])
        heading_tokens = approximate_token_count(_heading_prefix(unit.heading_path))
        candidate_tokens = approximate_token_count(candidate_body) + heading_tokens
        if current and (not same_heading or candidate_tokens > config.chunk_size):
            flush()
        current.append(unit)
    flush()
    return [chunk for chunk in packed if chunk["content"].strip()]
