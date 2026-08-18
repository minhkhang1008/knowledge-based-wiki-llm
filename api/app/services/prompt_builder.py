def connect(chunks: list[dict]) -> str:
    document = ["\n".join(f"{k} : {v}" for k,v in chunk.items()) for chunk in chunks]
    return "\n\n".join(map(str,document))

def build_rag_prompt(question: str, context_chunks: list[dict], chat_history: list[dict] | None = None) -> str:
    temp_chunk = []
    for index, chunk in enumerate(context_chunks, start = 1):
        formatted_chunk = connect([chunk])
        temp_chunk.append(f"[S{index}] {formatted_chunk}")
    completed_chunk = "\n\n".join(temp_chunk)

    system = f"""
    VAI TRÒ: Bạn là một trợ lý ảo chỉ trả lời câu hỏi dựa trên thông tin được cung cấp.

    NHIỆM VỤ: Đọc phần CÁC TÀI LIỆU để trả lời CÂU HỎI của người dùng.

    LƯU Ý CÁC NGUYÊN TẮC SAU:
    1. CHỈ trả lời dựa vào thông tin có sẵn trong CÁC TÀI LIỆU, không tự suy diễn, không dùng kiến thức bên ngoài các tài liệu được cung cấp.
    2. ĐẶT NHÃN TRÍCH DẪN [S#]: Đặt nhãn [S1], [S2],... ngay sau thông tin được sử dụng trong câu trả lời. KHÔNG tự tạo nhãn không tồn tại.
    3. KHÔNG DÙNG LỊCH SỬ LÀM NGUỒN SỰ THẬT: Lịch sử trò chuyện chỉ dùng để hiểu ngữ cảnh/đại từ trong câu hỏi nối tiếp. KHÔNG lấy thông tin trong Lịch sử trò chuyện để làm câu trả lời nếu thông tin đó không xuất hiện trong CÁC TÀI LIỆU.
    4. Nếu các tài liệu KHÔNG chứa thông tin để trả lời câu hỏi hoặc thông tin mơ hồ không đủ căn cứ, bạn PHẢI trả lời chính xác cụm từ sau: 'Tôi không tìm thấy thông tin này trong tài liệu.'. Không được cố gắng giải thích thêm hoặc bịa ra câu trả lời.
    5. Câu trả lời cần ngắn gọn, đi thẳng vào vấn đề, trung thực và khách quan.

    ĐỊNH DẠNG OUTPUT BẮT BUỘC:
    - Nếu trả lời được, câu trả lời PHẢI có ít nhất một nhãn nguồn [S#].
    - Ví dụ đúng: 'Dự án yêu cầu Python 3.11+ [S1].'
    - Câu trả lời có thông tin nhưng không có [S#] là không hợp lệ.
    - Nếu không thể gắn nguồn, chỉ trả lời đúng câu từ chối ở nguyên tắc 4.

    CÁC TÀI LIỆU:
    {completed_chunk}"""

    if (chat_history == None or chat_history == []):
        history = "Không có"
    else:
        history = connect(chat_history)
    full_prompt = f"{system}\n\nLỊCH SỬ TRÒ CHUYỆN:\n{history}\n\nCÂU HỎI:\n{question}"
    
    return full_prompt
