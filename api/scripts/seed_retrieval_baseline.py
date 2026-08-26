"""Seed the real retrieval baseline into the configured ChromaDB collection.

The corpus contains verified excerpts from the project's real Google Drive PDFs.
Only IDs listed in that corpus are replaced, so existing application data is not
deleted.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


API_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(API_ROOT))

DEFAULT_CORPUS_PATH = (
    API_ROOT / "tests" / "fixtures" / "retrieval_corpus_real.json"
)
REQUIRED_FIELDS = {
    "id",
    "article_id",
    "source_file",
    "source_url",
    "text",
}


def load_corpus(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(f"Không tìm thấy corpus: {path}")

    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Corpus không phải JSON hợp lệ: {exc}") from exc

    chunks = raw.get("chunks") if isinstance(raw, dict) else None
    if not isinstance(chunks, list) or not chunks:
        raise ValueError("Corpus phải có key 'chunks' là list không rỗng.")

    normalized: list[dict[str, str]] = []
    seen_ids: set[str] = set()

    for index, chunk in enumerate(chunks, start=1):
        if not isinstance(chunk, dict):
            raise ValueError(f"Chunk {index} phải là object/dict.")

        missing = REQUIRED_FIELDS - set(chunk)
        if missing:
            raise ValueError(
                f"Chunk {index} thiếu field: {', '.join(sorted(missing))}."
            )

        cleaned: dict[str, str] = {}
        for field in REQUIRED_FIELDS:
            value = chunk[field]
            if not isinstance(value, str) or not value.strip():
                raise ValueError(
                    f"Chunk {index}: '{field}' phải là chuỗi không rỗng."
                )
            cleaned[field] = value.strip()

        if cleaned["id"] in seen_ids:
            raise ValueError(f"Chunk ID bị trùng: {cleaned['id']}")
        seen_ids.add(cleaned["id"])
        normalized.append(cleaned)

    return normalized


async def seed_corpus(chunks: list[dict[str, str]]) -> None:
    from app.core.ollama_client import generate_embeddings
    from app.core.database import AsyncSessionLocal, init_db
    from app.models.article import Article
    from app.services.services_vector_db import collection
    from sqlalchemy.dialects.sqlite import insert

    await init_db()
    now = datetime.now(timezone.utc)
    async with AsyncSessionLocal() as session:
        for chunk in chunks:
            article_stmt = insert(Article).values(
                id=chunk["article_id"],
                document_id=chunk["article_id"],
                title=chunk["source_file"],
                content=chunk["text"],
                source_file=chunk["source_file"],
                created_at=now,
                updated_at=now,
            )
            article_stmt = article_stmt.on_conflict_do_update(
                index_elements=["id"],
                set_={
                    Article.title: article_stmt.excluded.title,
                    Article.content: article_stmt.excluded.content,
                    Article.source_file: article_stmt.excluded.source_file,
                    Article.updated_at: now,
                },
            )
            await session.execute(article_stmt)
        await session.commit()

    embeddings = await generate_embeddings([chunk["text"] for chunk in chunks])

    ids = [chunk["id"] for chunk in chunks]
    collection.delete(ids=ids)
    collection.upsert(
        ids=ids,
        embeddings=embeddings,
        documents=[chunk["text"] for chunk in chunks],
        metadatas=[
            {
                "article_id": chunk["article_id"],
                "source_file": chunk["source_file"],
                "source_url": chunk["source_url"],
                "dataset": "real-retrieval-baseline",
            }
            for chunk in chunks
        ],
    )

    stored = collection.get(ids=ids, include=["metadatas"])
    stored_ids = set(stored.get("ids") or [])
    missing_ids = set(ids) - stored_ids
    if missing_ids:
        raise RuntimeError(
            "ChromaDB thiếu chunk sau khi seed: "
            + ", ".join(sorted(missing_ids))
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Seed corpus thật dùng cho retrieval baseline."
    )
    parser.add_argument(
        "--corpus",
        type=Path,
        default=DEFAULT_CORPUS_PATH,
        help="Đường dẫn corpus JSON.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        chunks = load_corpus(args.corpus)
        asyncio.run(seed_corpus(chunks))
    except Exception as exc:
        print(f"Seed baseline thất bại: {type(exc).__name__}: {exc}")
        return 1

    print(
        f"Đã seed {len(chunks)} chunk dữ liệu thật vào collection 'chunks'."
    )
    print(
        "Nguồn: "
        + ", ".join(dict.fromkeys(chunk["source_file"] for chunk in chunks))
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
