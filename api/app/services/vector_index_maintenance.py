from __future__ import annotations
from app.services.services_vector_db import collection


def _validate_non_empty(value: str, field_name: str) -> str:
    
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} không được để rỗng")
    return value


def count_indexed_chunks() -> int:
    return collection.count()


def count_chunks_by_article_id(article_id: str) -> int:
    
    article_id = _validate_non_empty(article_id, "article_id")

    result = collection.get(
        where={"article_id": {"$eq": article_id}},
        include=[],
    )
    ids = result.get("ids") or []
    return len(ids)


def delete_chunks_by_article_id(article_id: str) -> int:
    
    
    article_id = _validate_non_empty(article_id, "article_id")

    matched = collection.get(
        where={"article_id": {"$eq": article_id}},
        include=[],
    )
    ids = matched.get("ids") or []

    if not ids:
        return 0

    collection.delete(ids=ids)
    return len(ids)


def delete_chunks_by_source_file(source_file: str) -> int:
  
    source_file = _validate_non_empty(source_file, "source_file")

    matched = collection.get(
        where={"source_file": {"$eq": source_file}},
        include=[],
    )
    ids = matched.get("ids") or []

    if not ids:
        return 0

    collection.delete(ids=ids)
    return len(ids)