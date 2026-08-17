import unittest

from app.services.chunking import ChunkConfig, chunk_from_markdown, chunk_pptx


class PptxChunkerTests(unittest.TestCase):
    def test_short_slides_keep_boundaries_and_metadata(self) -> None:
        markdown = """---
title: policy.pptx
total_slides: 2
---

## Chính sách nghỉ phép

* Nhân viên có 12 ngày phép

> **Speaker Notes:**
> Nội dung trình bày

---

## Liên hệ

* Gửi email cho HR

---
"""

        chunks = chunk_pptx(markdown, "policy.pptx")

        self.assertEqual(len(chunks), 2)
        self.assertNotIn("title: policy.pptx", chunks[0]["content"])
        self.assertIn("Speaker Notes", chunks[0]["content"])
        self.assertEqual(chunks[0]["metadata"]["slide_number"], 1)
        self.assertEqual(chunks[0]["metadata"]["page_number"], 1)
        self.assertEqual(
            chunks[0]["metadata"]["slide_title"],
            "Chính sách nghỉ phép",
        )
        self.assertEqual(chunks[1]["metadata"]["slide_number"], 2)
        self.assertNotIn("12 ngày phép", chunks[1]["content"])

    def test_long_slide_repeats_title_without_cross_slide_overlap(self) -> None:
        first_slide_words = " ".join(f"policy_{index}" for index in range(180))
        markdown = f"""## Chính sách nghỉ phép

{first_slide_words}

---

## Slide kế tiếp

NEXT_SLIDE_ONLY

---
"""

        chunks = chunk_pptx(
            markdown,
            "policy.pptx",
            ChunkConfig(chunk_size=80, overlap=20),
        )
        first_slide_chunks = [
            chunk
            for chunk in chunks
            if chunk["metadata"]["slide_number"] == 1
        ]
        second_slide_chunks = [
            chunk
            for chunk in chunks
            if chunk["metadata"]["slide_number"] == 2
        ]

        self.assertGreater(len(first_slide_chunks), 1)
        self.assertTrue(
            all(
                chunk["content"].startswith("## Chính sách nghỉ phép\n\n")
                for chunk in first_slide_chunks
            )
        )
        self.assertEqual(
            [chunk["metadata"]["chunk_part"] for chunk in first_slide_chunks],
            list(range(1, len(first_slide_chunks) + 1)),
        )
        self.assertEqual(len(second_slide_chunks), 1)
        self.assertNotIn("policy_", second_slide_chunks[0]["content"])
        self.assertEqual(
            second_slide_chunks[0]["content"],
            "## Slide kế tiếp\n\nNEXT_SLIDE_ONLY",
        )

    def test_registry_routes_pptx_and_supports_untitled_slide(self) -> None:
        chunks = chunk_from_markdown(
            "Nội dung không có heading\n\n---\n",
            "untitled.pptx",
            ".pptx",
        )

        self.assertEqual(len(chunks), 1)
        self.assertEqual(chunks[0]["metadata"]["slide_title"], "[Untitled Slide]")
        self.assertEqual(
            chunks[0]["content"],
            "## [Untitled Slide]\n\nNội dung không có heading",
        )


if __name__ == "__main__":
    unittest.main()
