"""Chunking for Excel (.xlsx / .xlsm / .xls) after conversion to Markdown."""

from __future__ import annotations

import re
from typing import Iterator

from app.services.chunking.chunker_registry import register
from app.services.chunking.config import ChunkConfig
from app.services.chunking.recursive import (
    approximate_token_count,
    is_table_line,
    recursive_split,
)

SHEET_HEADING_PATTERN = re.compile(r"^##\s+Sheet:\s*(.+)$", re.IGNORECASE)

def _split_markdown_row(line: str) -> list[str]:
    content = line.strip().strip("|")

    return [
        cell.strip().replace(r"\|", "|")
        for cell in re.split(r"(?<!\\)\|", content)
    ]

def _parse_markdown_table(table_lines: list[str]) -> tuple[list[str], list[list[str]]]:
    if len(table_lines) < 2:
        return [], []

    headers = _split_markdown_row(table_lines[0])
    data_rows: list[list[str]] = []

    for line in table_lines[2:]:
        cells = _split_markdown_row(line)
        if len(cells) < len(headers):
            cells.extend([""] * (len(headers) - len(cells)))
        data_rows.append(cells[: len(headers)])

    return headers, data_rows


def _format_excel_row(headers: list[str], row_values: list[str]) -> str:
    pairs = []
    for header, value in zip(headers, row_values):
        label = header.strip() or "Column"
        pairs.append(f"{label}: {value.strip()}")
    return " | ".join(pairs)


def _iter_excel_sheet_chunks(
    sheet_name: str,
    table_lines: list[str],
    source: str,
    config: ChunkConfig,
) -> Iterator[dict]:
    headers, data_rows = _parse_markdown_table(table_lines)
    if not headers:
        return

    for index, row_values in enumerate(data_rows, start=2):
        if not any(value.strip() for value in row_values):
            continue

        row_text = _format_excel_row(headers, row_values)
        parts = (
            [row_text]
            if approximate_token_count(row_text) <= config.chunk_size
            else recursive_split(row_text, config.chunk_size, config.overlap)
        )

        for part in parts:
            yield {
                "content": part,
                "metadata": {
                    "source_file": source,
                    "sheet": sheet_name,
                    "row": str(index),
                },
            }


def chunk_excel(
    markdown_text: str,
    source: str,
    config: ChunkConfig | None = None,
) -> list[dict]:
    """
    Split Excel-derived Markdown into one chunk per table row.

    Expects the format produced by ``excel_to_markdown``:
    ``## Sheet: <name>`` followed by a Markdown table.
    """
    config = config or ChunkConfig()
    chunks: list[dict] = []
    current_sheet = ""
    table_lines: list[str] = []

    def flush_table() -> None:
        nonlocal table_lines
        if current_sheet and table_lines:
            chunks.extend(
                _iter_excel_sheet_chunks(
                    current_sheet,
                    table_lines,
                    source,
                    config,
                )
            )
        table_lines = []

    for raw_line in markdown_text.splitlines():
        line = raw_line.rstrip()

        sheet_match = SHEET_HEADING_PATTERN.match(line)
        if sheet_match:
            flush_table()
            current_sheet = sheet_match.group(1).strip()
            continue

        if is_table_line(line):
            table_lines.append(line)
            continue

        if table_lines:
            flush_table()

    flush_table()
    return chunks


@register(".xlsx")
@register(".xlsm")
@register(".xls")
def chunk_excel_file(
    markdown_text: str,
    source: str,
    config: ChunkConfig | None = None,
) -> list[dict]:
    return chunk_excel(markdown_text, source, config)
