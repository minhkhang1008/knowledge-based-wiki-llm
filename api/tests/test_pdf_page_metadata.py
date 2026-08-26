import unittest

from app.services.chunking import ChunkConfig, chunk_from_markdown
from app.services.document_parser.pdf_converter import (
    BlockType,
    BoundingBox,
    DocumentBlock,
    DocumentLayoutSorter,
    MarkdownCompiler,
    PDFTextCleaner,
    LocalPDFParser,
)


class PdfPageMetadataRegressionTests(unittest.TestCase):
    def test_layout_sorter_keeps_pages_in_document_order(self) -> None:
        page_two = DocumentBlock(
            BlockType.PARAGRAPH,
            BoundingBox(0, 10, 100, 20),
            "Trang hai",
            page_number=2,
        )
        page_one = DocumentBlock(
            BlockType.PARAGRAPH,
            BoundingBox(0, 700, 100, 710),
            "Trang một",
            page_number=1,
        )

        sorted_blocks = DocumentLayoutSorter().sort_blocks([page_two, page_one])

        self.assertEqual([block.page_number for block in sorted_blocks], [1, 2])

    def test_markdown_emits_page_markers(self) -> None:
        blocks = [
            DocumentBlock(
                BlockType.PARAGRAPH,
                BoundingBox(0, 10, 100, 20),
                "Nội dung trang một",
                page_number=1,
            ),
            DocumentBlock(
                BlockType.PARAGRAPH,
                BoundingBox(0, 10, 100, 20),
                "Nội dung trang hai",
                page_number=2,
            ),
        ]

        markdown = MarkdownCompiler.compile(blocks)

        self.assertIn("<!-- page: 1 -->", markdown)
        self.assertIn("<!-- page: 2 -->", markdown)
        self.assertLess(markdown.index("trang một"), markdown.index("trang hai"))

    def test_cleaner_preserves_valid_si_units(self) -> None:
        text = "Công suất gồm 100 kW, 10 MW, 50 W; tụ điện 2 mF."

        self.assertEqual(PDFTextCleaner.clean(text), text)

    def test_cleaner_repairs_verified_private_use_punctuation(self) -> None:
        text = "Thonny \ue081IDE\ue082 - BƯỚC 1\ue092\u200bCài đặt"

        self.assertEqual(
            PDFTextCleaner.clean(text),
            "Thonny (IDE) - BƯỚC 1: Cài đặt",
        )

    def test_lowercase_bold_continuation_is_not_a_heading(self) -> None:
        self.assertFalse(
            LocalPDFParser._starts_like_heading(
                "làm việc của Thonny được chia thành hai vùng chính:"
            )
        )
        self.assertTrue(LocalPDFParser._starts_like_heading("BƯỚC 1: Cài đặt"))
        parser = LocalPDFParser.__new__(LocalPDFParser)
        self.assertEqual(
            parser._determine_block_type_by_font(
                "làm việc của Thonny được chia thành hai vùng chính:",
                16.0,
                "Inter-Bold",
                16.0,
                18.0,
                "Inter-Regular",
                {"Inter-Bold"},
            ),
            BlockType.PARAGRAPH,
        )

    def test_pdf_chunks_do_not_cross_pages_and_keep_page_number(self) -> None:
        markdown = """<!-- page: 1 -->
# Chính sách nghỉ phép

Nhân viên có 12 ngày phép mỗi năm.

<!-- page: 2 -->
# Quy trình đăng ký

Gửi yêu cầu trước ba ngày.
"""

        chunks = chunk_from_markdown(
            markdown,
            source="hr-policy.pdf",
            file_ext=".pdf",
            config=ChunkConfig(chunk_size=20, overlap=5),
        )

        self.assertEqual(
            {chunk["metadata"]["page_number"] for chunk in chunks},
            {1, 2},
        )
        for chunk in chunks:
            page_number = chunk["metadata"]["page_number"]
            if page_number == 1:
                self.assertNotIn("Gửi yêu cầu", chunk["content"])
            if page_number == 2:
                self.assertNotIn("12 ngày phép", chunk["content"])
            self.assertNotIn("<!-- page:", chunk["content"])


if __name__ == "__main__":
    unittest.main()
