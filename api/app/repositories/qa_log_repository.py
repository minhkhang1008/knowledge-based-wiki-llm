"""
Temporary in-memory implementation.

Task Hào Việt
Không thay đổi tên hàm, thứ tự tham số hoặc kiểu trả về.
"""

from typing import Any


_QA_LOGS: list[dict[str, Any]] = []


async def log_qa_interaction(
    session: Any,
    question: str,
    answer: str,
    sources: list[dict[str, Any]],
) -> None:
    """
    Lưu một lượt hỏi đáp.

    Mock hiện tại chỉ lưu trong bộ nhớ để các API có thể chạy độc lập.
    Implementation thật phải sử dụng AsyncSession được truyền vào.
    """
    _QA_LOGS.append(
        {
            "question": question,
            "answer": answer,
            "sources": sources,
        }
    )