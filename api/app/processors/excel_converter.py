from pathlib import Path
from xml.etree import ElementTree
from zipfile import ZipFile
from .converter_registry import register


NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}


def _escape_markdown_cell(value: object) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    return text.replace("|", r"\|").replace("\n", " ")


def _column_to_index(column: str) -> int:
    index = 0
    for char in column:
        index = index * 26 + (ord(char.upper()) - ord("A") + 1)
    return index - 1


def _cell_reference_to_indexes(reference: str) -> tuple[int, int]:
    column = "".join(char for char in reference if char.isalpha())
    row = "".join(char for char in reference if char.isdigit())
    return int(row) - 1, _column_to_index(column)


def _read_shared_strings(archive: ZipFile) -> list[str]:
    if "xl/sharedStrings.xml" not in archive.namelist():
        return []

    root = ElementTree.fromstring(archive.read("xl/sharedStrings.xml"))
    strings: list[str] = []
    for item in root.findall("m:si", NS):
        text_parts = [node.text or "" for node in item.findall(".//m:t", NS)]
        strings.append("".join(text_parts))
    return strings


def _read_workbook_sheets(archive: ZipFile) -> list[tuple[str, str]]:
    workbook = ElementTree.fromstring(archive.read("xl/workbook.xml"))
    relationships = ElementTree.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
    rel_map = {
        rel.attrib["Id"]: rel.attrib["Target"]
        for rel in relationships
        if rel.attrib.get("Type", "").endswith("/worksheet")
    }

    sheets: list[tuple[str, str]] = []
    for sheet in workbook.findall("m:sheets/m:sheet", NS):
        name = sheet.attrib["name"]
        relationship_id = sheet.attrib.get("{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id")
        target = rel_map.get(relationship_id, "")
        if target.startswith("/"):
            target = target.lstrip("/")
        if not target.startswith("xl/"):
            target = f"xl/{target.lstrip('/')}"
        sheets.append((name, target))
    return sheets


def _read_sheet_rows(archive: ZipFile, sheet_path: str, shared_strings: list[str]) -> list[list[str]]:
    root = ElementTree.fromstring(archive.read(sheet_path))
    sparse_rows: dict[int, dict[int, str]] = {}

    for row in root.findall(".//m:sheetData/m:row", NS):
        for cell in row.findall("m:c", NS):
            reference = cell.attrib.get("r")
            if not reference:
                continue

            row_index, col_index = _cell_reference_to_indexes(reference)
            cell_type = cell.attrib.get("t")
            value_node = cell.find("m:v", NS)
            inline_node = cell.find("m:is/m:t", NS)

            if cell_type == "s" and value_node is not None and value_node.text is not None:
                value = shared_strings[int(value_node.text)]
            elif inline_node is not None:
                value = inline_node.text or ""
            elif value_node is not None and value_node.text is not None:
                value = value_node.text
            else:
                value = ""

            sparse_rows.setdefault(row_index, {})[col_index] = value

    if not sparse_rows:
        return []

    max_row = max(sparse_rows)
    max_col = max(max(cols) for cols in sparse_rows.values())
    rows: list[list[str]] = []

    for row_index in range(max_row + 1):
        row_values = sparse_rows.get(row_index, {})
        rows.append([row_values.get(col_index, "") for col_index in range(max_col + 1)])

    while rows and not any(cell.strip() for cell in rows[-1]):
        rows.pop()

    return [row for row in rows if any(str(cell).strip() for cell in row)]


def _rows_to_markdown(rows: list[list[str]]) -> str:
    if not rows:
        return "_Sheet trống_\n"

    headers = [_escape_markdown_cell(cell) for cell in rows[0]]
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
    ]

    for row in rows[1:]:
        cells = [_escape_markdown_cell(cell) for cell in row]
        if len(cells) < len(headers):
            cells.extend([""] * (len(headers) - len(cells)))
        lines.append("| " + " | ".join(cells[: len(headers)]) + " |")

    return "\n".join(lines) + "\n"

@register(".xlsx")
@register(".xlsm")
def excel_to_markdown(file_path: str | Path) -> str:
    """Chuyển file Excel (.xlsx, .xlsm) sang Markdown, mỗi sheet thành một bảng."""
    print("Đang convert Excel:", file_path)
    path = Path(file_path)
    if path.suffix.lower() not in {".xlsx", ".xlsm"}:
        raise ValueError(f"Không phải file Excel hỗ trợ: {path}")

    with ZipFile(path) as archive:
        shared_strings = _read_shared_strings(archive)
        sections = [f"# {path.stem}\n"]

        for sheet_name, sheet_path in _read_workbook_sheets(archive):
            rows = _read_sheet_rows(archive, sheet_path, shared_strings)
            sections.append(f"\n## Sheet: {sheet_name}\n")
            sections.append(_rows_to_markdown(rows))

    return "\n".join(sections).strip() + "\n"
