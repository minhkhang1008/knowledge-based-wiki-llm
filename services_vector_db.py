import os
import chromadb
from dotenv import load_dotenv
load_dotenv()
#kết nối ChromaDB
persist_path = os.getenv("CHROMA_PERSIST_PATH", "./chroma_db")
client = chromadb.PersistentClient(path=persist_path)
#Lấy collection
collection = client.get_or_create_collection("chunks")
#hàm truy vấn
def search_similar_chunks(query_embedding: list[float], top_k: int = 5):
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k
    )
    #Parse dữ liệu
    output = []
    documents = results["documents"][0]
    metadatas = results["metadatas"][0]
    for doc, meta in zip(documents, metadatas):
        output.append({
            "text": doc,
            "article_id": meta["article_id"],
            "page": meta["page"]
        })
    return output