from app.core.ollama_client import generate_chat

# Khung hàm mới cho Tuần 4 để các bạn làm việc song song
async def process_rag_pipeline(question: str) -> dict:
    """
    TODO (Phú Thịnh): Ráp toàn bộ luồng RAG vào đây.
    Hiện tại đang là Mock Data để Viết Bảo có thể test API qa.py.
    """
    return {
        "answer": f"Đây là câu trả lời giả lập cho câu hỏi: '{question}'. Chờ Phú Thịnh hoàn thiện logic.",
        "sources": [],
        "no_answer_reason": None
    }


# Hàm cũ của Tuần 3 (Tuần 4 Thịnh sẽ tái cấu trúc lại hoặc gom vào hàm trên)
async def execute_llm_generation(prompt: str, raw_chunks: list[dict]):
    raw_answer = await generate_chat(prompt)
    if "Tôi không tìm thấy thông tin này" in raw_answer:
        return {"answer": raw_answer, "sources": [], "no_answer_reason": "out_of_scope"}
    else:
        return {"answer": raw_answer, "sources": raw_chunks, "no_answer_reason": None}