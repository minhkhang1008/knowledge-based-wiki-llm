"""
Temporary in-memory implementation.

Task Hào Việt
Không thay đổi tên hàm, thứ tự tham số hoặc kiểu trả về.
"""
from sqlalchemy import insert 
from typing import Any
from app.models.qa_log import QALog
from sqlalchemy.ext.asyncio import AsyncSession 
from datetime import datetime,timezone
async def log_qa_interaction(
    session: AsyncSession,
    question: str,
    answer: str,
    sources: list[dict[str, Any]],
) -> None:
    """
    Lưu một lượt hỏi đáp.

    Mock hiện tại chỉ lưu trong bộ nhớ để các API có thể chạy độc lập.
    Implementation thật phải sử dụng AsyncSession được truyền vào.
    """
    try:
        stmt = insert(QALog).values(
            question= question,
            answer= answer, 
            sources= sources, 
            created_at= datetime.now(timezone.utc),
        )
        await session.execute(stmt)
        await session.commit()
    except Exception: 
        await session.rollback() 
        raise