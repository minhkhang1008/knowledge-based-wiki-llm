from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path
from typing import Any

API_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(API_ROOT))


def _shorten(text: str | None, max_length: int = 100) -> str:
    if not text:
        return "(không có text)"
    flat = " ".join(text.split())
    if len(flat) <= max_length:
        return flat
    return flat[: max_length - 3] + "..."


async def _fetch_all_articles() -> dict[str, dict[str, Any]]:
    """
    Đọc toàn bộ bảng articles trực tiếp (không qua list_articles vì hàm đó
    giới hạn tối đa 100 dòng/lần — integrity check cần thấy TOÀN BỘ bảng).
    """
    from app.core.database import AsyncSessionLocal
    from app.models.article import Article
    from sqlalchemy import select

    articles: dict[str, dict[str, Any]] = {}

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Article))
        for row in result.scalars().all():
            articles[row.id] = {
                "content": row.content,
                "source_file": row.source_file,
                "updated_at": row.updated_at,
            }

    return articles


def _fetch_all_chunks() -> dict[str, Any]:
    from app.services.services_vector_db import collection

    return collection.get(include=["metadatas", "documents"])


def analyze(
    chunks_raw: dict[str, Any],
    articles: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    ids = chunks_raw.get("ids") or []
    metadatas = chunks_raw.get("metadatas") or []
    documents = chunks_raw.get("documents") or []

    empty_metadata_ids: list[str] = []
    missing_both_fields_ids: list[str] = []
    orphan_article_chunk_ids: list[str] = []
    orphan_article_ids: set[str] = set()
    stale_content_chunk_ids: list[str] = []
    chunk_count_by_article: dict[str, int] = {}
    chunk_count_by_source_file: dict[str, int] = {}

    for i, chunk_id in enumerate(ids):
        meta = metadatas[i] if i < len(metadatas) else None
        doc = documents[i] if i < len(documents) else None

        if not meta:
            empty_metadata_ids.append(chunk_id)
            continue

        article_id = meta.get("article_id")
        source_file = meta.get("source_file")

        has_article_id = isinstance(article_id, str) and article_id.strip()
        has_source_file = isinstance(source_file, str) and source_file.strip()

        if not has_article_id and not has_source_file:
            missing_both_fields_ids.append(chunk_id)
            continue

        if has_article_id:
            chunk_count_by_article[article_id] = (
                chunk_count_by_article.get(article_id, 0) + 1
            )

            article = articles.get(article_id)
            if article is None:
                orphan_article_chunk_ids.append(chunk_id)
                orphan_article_ids.add(article_id)
            else:
                current_content = article.get("content") or ""
                chunk_text = (doc or "").strip()
                if chunk_text and chunk_text not in current_content:
                    stale_content_chunk_ids.append(chunk_id)

        if has_source_file:
            chunk_count_by_source_file[source_file] = (
                chunk_count_by_source_file.get(source_file, 0) + 1
            )

    return {
        "total_chunks": len(ids),
        "empty_metadata_ids": empty_metadata_ids,
        "missing_both_fields_ids": missing_both_fields_ids,
        "orphan_article_chunk_ids": orphan_article_chunk_ids,
        "orphan_article_ids": orphan_article_ids,
        "stale_content_chunk_ids": stale_content_chunk_ids,
        "chunk_count_by_article": chunk_count_by_article,
        "chunk_count_by_source_file": chunk_count_by_source_file,
    }


def print_report(report: dict[str, Any]) -> None:
    print("=" * 70)
    print("BÁO CÁO INDEX INTEGRITY")
    print("=" * 70)
    print(f"Tổng số chunk trong ChromaDB: {report['total_chunks']}\n")

    print(
        "1) Chunk metadata rỗng hoàn toàn: "
        f"{len(report['empty_metadata_ids'])}"
    )
    for cid in report["empty_metadata_ids"][:20]:
        print(f"   - {cid}")
    if len(report["empty_metadata_ids"]) > 20:
        print(f"   ... và {len(report['empty_metadata_ids']) - 20} chunk khác")

    print(
        "\n2) Chunk thiếu CẢ article_id lẫn source_file: "
        f"{len(report['missing_both_fields_ids'])}"
    )
    for cid in report["missing_both_fields_ids"][:20]:
        print(f"   - {cid}")
    if len(report["missing_both_fields_ids"]) > 20:
        print(
            f"   ... và {len(report['missing_both_fields_ids']) - 20} "
            "chunk khác"
        )

    print(
        "\n3) Chunk orphan (article_id không còn tồn tại trong bảng "
        f"articles): {len(report['orphan_article_chunk_ids'])}"
    )
    for cid in report["orphan_article_chunk_ids"][:20]:
        print(f"   - {cid}")
    if len(report["orphan_article_chunk_ids"]) > 20:
        print(
            f"   ... và {len(report['orphan_article_chunk_ids']) - 20} "
            "chunk khác"
        )

    print(
        "\n4) Chunk NGHI NGỜ chứa nội dung cũ sau khi Article đã update "
        f"(heuristic, cần review thủ công): "
        f"{len(report['stale_content_chunk_ids'])}"
    )
    for cid in report["stale_content_chunk_ids"][:20]:
        print(f"   - {cid}")
    if len(report["stale_content_chunk_ids"]) > 20:
        print(
            f"   ... và {len(report['stale_content_chunk_ids']) - 20} "
            "chunk khác"
        )

    print("\n5) Số chunk theo article_id:")
    if not report["chunk_count_by_article"]:
        print("   (không có)")
    orphan_article_ids = report.get("orphan_article_ids", set())
    for article_id, count in sorted(
        report["chunk_count_by_article"].items()
    ):
        flag = "  <-- ORPHAN (article đã bị xóa)" if article_id in orphan_article_ids else ""
        print(f"   - {article_id}: {count} chunk{flag}")

    print("\n   Số chunk theo source_file:")
    if not report["chunk_count_by_source_file"]:
        print("   (không có)")
    for source_file, count in sorted(
        report["chunk_count_by_source_file"].items()
    ):
        print(f"   - {source_file}: {count} chunk")

    total_problems = (
        len(report["empty_metadata_ids"])
        + len(report["missing_both_fields_ids"])
        + len(report["orphan_article_chunk_ids"])
        + len(report["stale_content_chunk_ids"])
    )
    print("\n" + "=" * 70)
    if total_problems == 0:
        print("KẾT LUẬN: Không phát hiện vấn đề nào. Index sạch.")
    else:
        print(
            f"KẾT LUẬN: Phát hiện {total_problems} chunk có vấn đề. "
            "Chạy lại với --cleanup để xóa (sau khi đã review kỹ, "
            "đặc biệt là các case 'nghi ngờ nội dung cũ' ở mục 4)."
        )
    print("=" * 70)


def cleanup(report: dict[str, Any]) -> None:
    from app.services.services_vector_db import collection
    from app.services.vector_index_maintenance import (
        delete_chunks_by_article_id,
    )

    deleted_total = 0

    # 1) Metadata rỗng hoàn toàn / thiếu cả article_id & source_file
    #    -> không có field nào để xóa "theo article_id" nên xóa trực tiếp theo id.
    direct_delete_ids = list(
        dict.fromkeys(
            report["empty_metadata_ids"] + report["missing_both_fields_ids"]
        )
    )
    if direct_delete_ids:
        collection.delete(ids=direct_delete_ids)
        deleted_total += len(direct_delete_ids)
        print(
            f"Đã xóa {len(direct_delete_ids)} chunk metadata rỗng / "
            "thiếu article_id & source_file."
        )

    # 2) Chunk orphan -> tái sử dụng delete_chunks_by_article_id() có sẵn
    #    trong vector_index_maintenance.py thay vì viết lại logic xóa.
    for article_id in report["orphan_article_ids"]:
        removed = delete_chunks_by_article_id(article_id)
        deleted_total += removed
        print(
            f"Đã xóa {removed} chunk orphan của article_id={article_id!r} "
            "(article không còn tồn tại)."
        )

    # 3) Chunk nghi ngờ chứa nội dung cũ -> xóa trực tiếp theo id vì chỉ
    #    một phần chunk của article đó là cũ, không thể xóa cả article_id.
    stale_ids = report["stale_content_chunk_ids"]
    if stale_ids:
        collection.delete(ids=stale_ids)
        deleted_total += len(stale_ids)
        print(f"Đã xóa {len(stale_ids)} chunk nghi ngờ chứa nội dung cũ.")

    if deleted_total == 0:
        print("Không có chunk nào cần xóa.")
    else:
        print(f"\nTổng cộng đã xóa {deleted_total} chunk.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Kiểm tra tính toàn vẹn của ChromaDB index."
    )
    parser.add_argument(
        "--cleanup",
        action="store_true",
        help=(
            "Thực sự xóa các chunk có vấn đề đã phát hiện. "
            "Mặc định KHÔNG bật (chỉ đọc & báo cáo)."
        ),
    )
    return parser.parse_args()


async def main_async(cleanup_mode: bool) -> int:
    try:
        chunks_raw = _fetch_all_chunks()
    except Exception as exc:
        print(f"Không đọc được ChromaDB collection 'chunks': {exc}")
        return 1

    try:
        articles = await _fetch_all_articles()
    except Exception as exc:
        print(f"Không đọc được bảng articles (SQLite): {exc}")
        return 1

    report = analyze(chunks_raw, articles)
    print_report(report)

    if cleanup_mode:
        total_problems = (
            len(report["empty_metadata_ids"])
            + len(report["missing_both_fields_ids"])
            + len(report["orphan_article_chunk_ids"])
            + len(report["stale_content_chunk_ids"])
        )
        if total_problems == 0:
            print("\n--cleanup: không có gì để xóa.")
        else:
            print("\n--cleanup: đang xóa các chunk có vấn đề...")
            cleanup(report)

    return 0


def main() -> int:
    args = parse_args()
    return asyncio.run(main_async(args.cleanup))


if __name__ == "__main__":
    raise SystemExit(main())