import os
import chromadb
import sys
#sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
from dotenv import load_dotenv
from app.core.ollama_client import generate_embedding

load_dotenv()

# 3.1: Kết nối ChromaDB
persist_path = os.getenv("CHROMA_PERSIST_PATH", "./chroma_db")
client = chromadb.PersistentClient(path=persist_path)

# Lấy hoặc tạo collection "chunks"
collection = client.get_or_create_collection("chunks")

# 3.2: Hàm truy vấn (Search)
def search_similar_chunks(query_embedding: list[float], top_k: int = 5) -> list[dict]:
    THRESHOLD = 0.7
    """
    Tìm kiếm top_k đoạn văn bản có độ tương đồng cao nhất từ ChromaDB.
    Trả về một danh sách các dictionary đã được chuẩn hóa format.
    """
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k
    )
    
    output = []
    
    # Kiểm tra an toàn: Nếu không tìm thấy kết quả hoặc cấu trúc trả về trống
    if not results or not results.get("documents") or not results["documents"][0]:
        return output
        
    # Lấy ra danh sách document và metadata của query đầu tiên
    documents = results["documents"][0]
    # Phòng trường hợp metadatas là None
    metadatas = results["metadatas"][0] if results.get("metadatas") else []

    # Lấy thêm danh sách distances (khoảng cách ngữ nghĩa) do ChromaDB trả về
    distances = results["distances"][0] if results.get("distances") else []
    # 3.3: Bóc tách dữ liệu (Parsing Data) an toàn
    for doc,meta,distance in zip(documents, metadatas,distances):

        # KIỂM TRA THRESHOLD: Nếu khoảng cách vượt quá 0.7, bỏ qua đoạn văn này
        if distance > THRESHOLD:
            continue

        # Phòng trường hợp một chunk cụ thể nào đó bị thiếu metadata (meta là None)
        meta_dict = meta if meta is not None else {}
        
        output.append({
            "text": doc,
            "article_id": meta_dict.get("article_id", "Unknown"),  # Dùng .get() để tránh lỗi KeyError
            "page": meta_dict.get("page", None),                   # Trả về None hoặc số trang mặc định nếu thiếu
            "distance": distance                                   # (Tuỳ chọn) Trả về thêm distance để dễ debug
        })
        
    return output

async def semantic_search_logic(query_text: str) -> list[dict]:
    
    # Bước 1: Gọi hàm của thành viên khác để đổi chữ thành số
    vector = await generate_embedding(query_text)
    
    # Bước 2: Cầm vector này truyền vào hàm lọc vừa làm ở trên
    clean_chunks = search_similar_chunks(vector, top_k=5)
    
    # Bước 3: Trả thẳng danh sách clean_chunks này ra ngoài
    return clean_chunks
