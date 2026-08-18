import os
import chromadb
from dotenv import load_dotenv
from app.core.ollama_client import generate_embedding

load_dotenv()

# 3.1: Kết nối ChromaDB
persist_path = os.getenv("CHROMA_PERSIST_PATH", "./chroma_db")
client = chromadb.PersistentClient(path=persist_path)

# Lấy hoặc tạo collection "chunks"
collection = client.get_or_create_collection("chunks")

# Export để caller (router/API layer) dùng làm default top_k khi build request, tránh hardcode số 5 rải rác nhiều nơi
# Không dùng làm default trong chữ ký hàm vì top_k=5 là public interface cố định
RAG_TOP_K = int(os.getenv("RAG_TOP_K", 5))
# Embedding được L2-normalize trước khi index/query, vì vậy khoảng cách không
# phụ thuộc vào độ lớn vector thô của nomic-embed-text.
RAG_DISTANCE_THRESHOLD = float(os.getenv("RAG_DISTANCE_THRESHOLD", 0.68))

# Các field filter được hỗ trợ, dùng để validate + tránh lọt field lạ vào where
SUPPORTED_FILTER_FIELDS = {"article_id", "source_file"}


def _validate_top_k(top_k: int) -> None:
    if not isinstance(top_k, int) or isinstance(top_k, bool) or top_k <= 0:
        raise ValueError("top_k phải lớn hơn 0.")


def _build_where_clause(filters: dict[str, str] | None) -> dict | None:
    """
    Chuyển filters (dict đơn giản) thành cú pháp `where` hợp lệ của ChromaDB.

    - filters None hoặc rỗng -> trả về None (không gửi where vào query).
    - Chỉ hỗ trợ các field trong SUPPORTED_FILTER_FIELDS (article_id, source_file);
      field nào ngoài danh sách này -> raise ValueError, không âm thầm bỏ qua,
      để tránh caller tưởng đã lọc theo field đó nhưng thực chất không có filter.
    - Trong các field hợp lệ, value rỗng/None -> bỏ qua field đó (coi như không lọc).
    - 1 field hợp lệ có value -> {"field": {"$eq": value}}
    - >1 field hợp lệ có value -> {"$and": [{"field1": {"$eq": v1}}, {"field2": {"$eq": v2}}]}
    """
    if not filters:
        return None

    unsupported = [field for field in filters if field not in SUPPORTED_FILTER_FIELDS]
    if unsupported:
        supported = ", ".join(sorted(SUPPORTED_FILTER_FIELDS))
        raise ValueError(
            f"Filter không được hỗ trợ: {', '.join(unsupported)}. Chỉ hỗ trợ: {supported}."
        )

    clauses = [
        {field: {"$eq": value}}
        for field, value in filters.items()
        if value
    ]

    if not clauses:
        return None

    if len(clauses) == 1:
        return clauses[0]

    return {"$and": clauses}


def search_similar_chunks(
    query_embedding: list[float],
    top_k: int = 5,
    filters: dict[str, str] | None = None,
) -> list[dict]:

    _validate_top_k(top_k)

    output: list[dict] = []

    if not query_embedding:
        return output

    where_clause = _build_where_clause(filters)

    query_kwargs = {
        "query_embeddings": [query_embedding],
        "n_results": top_k,
    }
    if where_clause is not None:
        query_kwargs["where"] = where_clause

    results = collection.query(**query_kwargs)

    if not results or not results.get("documents") or not results["documents"][0]:
        return output

    documents = results["documents"][0] or []

    metadatas_raw = results.get("metadatas")
    metadatas = metadatas_raw[0] if metadatas_raw and metadatas_raw[0] is not None else []

    distances_raw = results.get("distances")
    distances = distances_raw[0] if distances_raw and distances_raw[0] is not None else []

    for i, doc in enumerate(documents):
        meta = metadatas[i] if i < len(metadatas) else None
        distance = distances[i] if i < len(distances) else None

        if distance is not None and distance > RAG_DISTANCE_THRESHOLD:
            continue

        meta_dict = meta if meta is not None else {}

        output.append({
            "text": doc,
            "article_id": meta_dict.get("article_id"),
            "source_file": meta_dict.get("source_file"),
            "page_number": meta_dict.get("page_number"),
            "distance": distance,
        })

    output.sort(key=lambda x: (x["distance"] is None, x["distance"]))

    return output


async def semantic_search_logic(
    query_text: str,
    top_k: int = 5,
    filters: dict[str, str] | None = None,
) -> list[dict]:
    # Validate trước khi gọi embedding (Ollama) để tránh tốn 1 lần gọi network
    # không cần thiết khi top_k đã sai ngay từ đầu.
    _validate_top_k(top_k)

    # Bước 1: Gọi hàm của thành viên khác để đổi chữ thành số
    vector = await generate_embedding(query_text)

    clean_chunks = search_similar_chunks(vector, top_k=top_k, filters=filters)

    return clean_chunks
