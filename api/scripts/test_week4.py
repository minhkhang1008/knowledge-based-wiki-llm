import asyncio
import sys
import os
from pathlib import Path

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.database import init_db, AsyncSessionLocal
from app.models.qa_log import log_qa_interaction, QALog
from sqlalchemy import select
from app.services.prompt_builder import build_rag_prompt
from app.services.rag_service import process_rag_pipeline

async def run_integration_test():
    print("=== BẮT ĐẦU TEST TÍCH HỢP TUẦN 4 (HÀO VIỆT & PHÚ THỊNH) ===\n")
    
    # ---------------------------------------------------------
    # TEST 1: Khởi tạo Database (Task của Hào Việt)
    # ---------------------------------------------------------
    print("⏳ TEST 1: Khởi tạo Database SQLite Async...")
    try:
        await init_db()
        db_path = Path("../knowledge_base.db")
        print("   ✅ Thành công: Lệnh init_db không báo lỗi.")
    except Exception as e:
        print(f"   ❌ Thất bại: Lỗi khi init_db: {e}")

    # ---------------------------------------------------------
    # TEST 2: Prompt Builder & Multi-turn Chat (Task của Hào Việt)
    # ---------------------------------------------------------
    print("\n⏳ TEST 2: Build Prompt kèm Lịch sử chat...")
    try:
        mock_chunks = [{"source_file": "doc1.txt", "text": "LLM là mô hình ngôn ngữ lớn."}]
        mock_history = [
            {"question": "AI là gì?", "answer": "Trí tuệ nhân tạo."}
        ]
        prompt = build_rag_prompt("LLM là gì?", mock_chunks, mock_history)
        if "LỊCH SỬ TRÒ CHUYỆN" in prompt and "User: AI là gì?" in prompt:
            print("   ✅ Thành công: Prompt đã nối lịch sử chat chuẩn xác.")
        else:
            print("   ❌ Thất bại: Prompt thiếu lịch sử chat.")
    except Exception as e:
        print(f"   ❌ Thất bại: Lỗi hàm build_rag_prompt: {e}")

    # ---------------------------------------------------------
    # TEST 3: RAG Pipeline & Chặn Hallucination (Task của Phú Thịnh)
    # ---------------------------------------------------------
    print("\n⏳ TEST 3: RAG Pipeline & Chặn Ảo giác (Cần bật sẵn Ollama)...")
    try:
        # Giả lập câu hỏi KHÔNG có trong tài liệu để test chức năng chặn ảo giác
        out_of_scope_question = "Thời tiết sao Hỏa hôm nay thế nào?"
        result = await process_rag_pipeline(out_of_scope_question)
        
        if result.get("no_answer_reason") == "out_of_scope":
            print(f"   ✅ Thành công: Đã chặn ảo giác tốt! AI trả lời: {result.get('answer')}")
        else:
            print(f"   ❌ Thất bại (Hallucination): Hệ thống không chặn được. AI trả lời: {result.get('answer')}")
    except Exception as e:
        print(f"   ⚠️ Lỗi Pipeline (Có thể do chưa bật Ollama/ChromaDB): {e}")

    # ---------------------------------------------------------
    # TEST 4: Ghi Log Database (Task của Hào Việt)
    # ---------------------------------------------------------
    print("\n⏳ TEST 4: Ghi Log QA vào Database...")
    try:
        async with AsyncSessionLocal() as session:
            await log_qa_interaction(
                session=session,
                question="Câu hỏi test log",
                answer="Câu trả lời test log",
                source=[{"doc": "test"}]
            )
            
            # Đọc lại để xác minh
            stmt = select(QALog).where(QALog.question == "Câu hỏi test log")
            res = await session.execute(stmt)
            saved_log = res.scalar_one_or_none()
            
            if saved_log:
                print(f"   ✅ Thành công: Đã ghi và đọc log ID {saved_log.id} từ SQLite.")
            else:
                print("   ❌ Thất bại: Không tìm thấy log vừa ghi.")
    except Exception as e:
        print(f"   ❌ Thất bại: Lỗi khi thao tác QA Log: {e}")

if __name__ == "__main__":
    asyncio.run(run_integration_test())