from __future__ import annotations

from app.services.chunking import ChunkConfig, chunk_from_markdown
from app.services.chunking.recursive import approximate_token_count
from app.services.document_parser.pdf_converter import (
    BlockType,
    BoundingBox,
    DocumentBlock,
    MarkdownCompiler,
    RepeatedMarginFilter,
)
from app.services.ocr.ocr_utils import _group_words_into_regions


def test_image_chunker_keeps_ocr_metadata_and_skips_filename_only() -> None:
    with_ocr = """![receipt](images/receipt.png)

<!-- ocr-meta: engine=easyocr; confidence=0.8750; regions=2 -->
> **Nội dung nhận dạng từ ảnh:**
> Tổng tiền 120.000 đồng
> Ngày 18/08/2026
"""
    chunks = chunk_from_markdown(with_ocr, "receipt.png", ".png")

    assert len(chunks) == 1
    assert "Tổng tiền" in chunks[0]["content"]
    assert chunks[0]["metadata"]["ocr_engine"] == "easyocr"
    assert chunks[0]["metadata"]["ocr_confidence"] == 0.875
    assert chunks[0]["metadata"]["image_number"] == 1

    filename_only = "![receipt](images/receipt.png)\n"
    assert chunk_from_markdown(filename_only, "receipt.png", ".png") == []


def test_large_pdf_table_repeats_header_and_never_crosses_page() -> None:
    rows = "\n".join(f"| SP-{index} | {index}.000 |" for index in range(30))
    markdown = f"""<!-- page: 1 -->
# Bảng giá

| Sản phẩm | Giá |
|---|---|
{rows}

<!-- page: 2 -->
# Điều khoản

Chỉ áp dụng trong tháng tám.
"""
    chunks = chunk_from_markdown(
        markdown,
        "price-list.pdf",
        ".pdf",
        ChunkConfig(chunk_size=45, overlap=5),
    )
    table_chunks = [chunk for chunk in chunks if chunk["metadata"]["block_type"] == "table"]

    assert len(table_chunks) > 1
    assert all("| Sản phẩm | Giá |" in chunk["content"] for chunk in table_chunks)
    assert all(chunk["metadata"]["page_number"] == 1 for chunk in table_chunks)
    assert all("Điều khoản" not in chunk["content"] for chunk in table_chunks)


def test_pdf_heading_path_is_repeated_on_long_chunks() -> None:
    body = " ".join(f"nội_dung_{index}." for index in range(100))
    markdown = f"<!-- page: 3 -->\n# Chương 1\n## Cài đặt\n\n{body}"
    chunks = chunk_from_markdown(
        markdown,
        "guide.pdf",
        ".pdf",
        ChunkConfig(chunk_size=35, overlap=5),
    )

    assert len(chunks) > 1
    assert all(chunk["content"].startswith("Chương 1 > Cài đặt") for chunk in chunks)
    assert all(chunk["metadata"]["heading_path"] == "Chương 1 > Cài đặt" for chunk in chunks)
    assert all(approximate_token_count(chunk["content"]) <= 45 for chunk in chunks)


def test_repeated_margin_filter_removes_header_but_keeps_body() -> None:
    blocks: list[DocumentBlock] = []
    for page in range(1, 5):
        blocks.extend([
            DocumentBlock(BlockType.PARAGRAPH, BoundingBox(0, 5, 100, 15), "ACME CONFIDENTIAL", page_number=page),
            DocumentBlock(BlockType.PARAGRAPH, BoundingBox(0, 100, 100, 120), f"Nội dung riêng trang {page}", page_number=page),
            DocumentBlock(BlockType.PARAGRAPH, BoundingBox(0, 790, 100, 800), "Tài liệu nội bộ", page_number=page),
        ])

    filtered = RepeatedMarginFilter().filter(blocks)
    texts = [block.content for block in filtered]

    assert "ACME CONFIDENTIAL" not in texts
    assert "Tài liệu nội bộ" not in texts
    assert len([text for text in texts if text.startswith("Nội dung riêng")]) == 4


def test_pdf_image_ocr_metadata_survives_markdown_and_chunking() -> None:
    markdown = MarkdownCompiler.compile([
        DocumentBlock(
            BlockType.IMAGE,
            BoundingBox(10, 20, 200, 100),
            "",
            ocr_text="Sơ đồ quy trình phê duyệt",
            page_number=2,
            ocr_confidence=0.91,
            ocr_engine="easyocr",
        )
    ])
    chunks = chunk_from_markdown(markdown, "workflow.pdf", ".pdf")

    assert len(chunks) == 1
    assert chunks[0]["metadata"]["page_number"] == 2
    assert chunks[0]["metadata"]["ocr_confidence"] == 0.91
    assert chunks[0]["metadata"]["block_type"] == "image_ocr"


def test_ocr_regions_preserve_reading_order_and_confidence() -> None:
    regions = _group_words_into_regions([
        {"text": "sau", "x0": 50, "top": 20, "x1": 80, "bottom": 30, "confidence": 0.8},
        {"text": "Xin", "x0": 0, "top": 5, "x1": 20, "bottom": 15, "confidence": 0.9},
        {"text": "chào", "x0": 25, "top": 5, "x1": 45, "bottom": 15, "confidence": 0.7},
    ])

    assert [region.text for region in regions] == ["Xin chào", "sau"]
    assert regions[0].confidence == 0.8


def test_ocr_regions_use_column_major_order_for_two_columns() -> None:
    words = [
        {"text": "L1", "x0": 0, "top": 0, "x1": 30, "bottom": 10, "confidence": 1.0},
        {"text": "R1", "x0": 200, "top": 0, "x1": 230, "bottom": 10, "confidence": 1.0},
        {"text": "L2", "x0": 0, "top": 20, "x1": 30, "bottom": 30, "confidence": 1.0},
        {"text": "R2", "x0": 200, "top": 20, "x1": 230, "bottom": 30, "confidence": 1.0},
    ]

    regions = _group_words_into_regions(words)

    assert [region.text for region in regions] == ["L1", "L2", "R1", "R2"]
