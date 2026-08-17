"""Dev CLI: python -m app <file.md> --ext .docx"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="Chunk Markdown theo định dạng file gốc")
    parser.add_argument("markdown_file", type=Path, help="Đường dẫn file .md (output từ parser)")
    parser.add_argument(
        "--ext",
        required=True,
        help="Phần mở rộng file gốc, vd. .docx hoặc .xlsx",
    )
    parser.add_argument("--source", default=None, help="Tên nguồn trong metadata (mặc định: tên file)")
    args = parser.parse_args()

    if not args.markdown_file.is_file():
        print(f"Không tìm thấy file: {args.markdown_file}", file=sys.stderr)
        sys.exit(1)

    from app.services.chunking import chunk_markdown_file

    chunks = chunk_markdown_file(
        args.markdown_file,
        source_ext=args.ext,
        source=args.source,
    )
    print(json.dumps(chunks, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
