def connect(chunks: list[dict]) -> str:
    document = ["\n".join(f"{k} : {v}" for k,v in chunk.items()) for chunk in chunks]
    return "\n\n".join(map(str,document))
def build_rag_prompt(question: str, context_chunks: list[dict], chat_history: list[dict] = []) -> str:
    system = "VAI TRÒ: Bạn là một trợ lý ảo chỉ trả lời câu hỏi dựa trên thông tin được cung cấp.\nNHIỆM VỤ: đọc phần các tài liệu để trả lời câu hỏi của người dùng\nLƯU Ý các NGUYÊN TẮC sau:\n1. CHỈ trả lời dựa vào thông tin có sẵn trong các tài liệu, không tự suy diễn, không dùng kiến thức bên ngoài các tài liệu được cung cấp.\n2. Nếu các tài liệu KHÔNG chứa thông tin để trả lời câu hỏi hoặc thông tin mơ hồ không đủ căn cứ, bạn PHẢI trả lời chính xác cụm từ sau: 'Tôi không tìm thấy thông tin này'.Không được cố gắng giải thích thêm hoặc bịa ra câu trả lời.\n3. Câu trả lời cần ngắn gọn, đi thẳng vào vấn đề, trung thực và khách quan.\n\nCÁC TÀI LIỆU:\n"
    document = connect(context_chunks)
    history = connect(chat_history)
    full_prompt = f"{system}{document}LỊCH SỬ TRÒ CHUYỆN:\n{history}CÂU HỎI:\n{question}"
    return full_prompt
