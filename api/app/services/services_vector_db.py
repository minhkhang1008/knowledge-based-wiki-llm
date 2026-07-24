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

RAG_TOP_K = int(os.getenv("RAG_TOP_K", 5))
RAG_DISTANCE_THRESHOLD = float(os.getenv("RAG_DISTANCE_THRESHOLD", 0.7))

def search_similar_chunks(
    query_embedding: list[float],
    top_k: int = 5,
    filters: dict[str, str] | None = None,
) -> list[dict]:
    
    output: list[dict] = []

    if not query_embedding:
        return output

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
    )

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
    # Bước 1: Gọi hàm của thành viên khác để đổi chữ thành số
    vector = await generate_embedding(query_text)

    clean_chunks = search_similar_chunks(vector, top_k=top_k, filters=filters)

    return clean_chunks