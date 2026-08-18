"""
Đánh giá chất lượng retrieval của hệ thống RAG.

CHẾ ĐỘ CHẠY:

1) DEFAULT — không cần Ollama/ChromaDB:
   Dùng FAKE_CORPUS để kiểm tra logic đánh giá.

       python scripts/evaluate_retrieval.py

2) INTEGRATION — dùng Ollama và ChromaDB thật:
   Chỉ chạy khi RUN_RAG_INTEGRATION=1. Nếu dữ liệu hoặc Ollama chưa sẵn sàng,
   script thông báo rõ và bỏ qua.

       RUN_RAG_INTEGRATION=1 python scripts/evaluate_retrieval.py

Dataset:
    tests/fixtures/retrieval_cases.json

Script hiển thị:
- Question
- Expected source
- Retrieved sources
- Pass/Fail
- Recall@k
- Tỷ lệ nhận diện đúng câu hỏi không có context
- Số case pass trên tổng số case
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any, Awaitable, Callable


# Chạy file từ thư mục api:
#     cd api
#     python scripts/evaluate_retrieval.py
API_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(API_ROOT))

DEFAULT_DATASET_PATH = (
    API_ROOT / "tests" / "fixtures" / "retrieval_cases.json"
)
DEFAULT_TOP_K = 5
MOCK_DISTANCE_THRESHOLD = 0.8
SUPPORTED_FILTER_FIELDS = {"article_id", "source_file"}


# =============================================================================
# FAKE COLLECTION — dùng cho chế độ DEFAULT
# =============================================================================

FAKE_CORPUS: list[dict[str, Any]] = [
    {
        "text": (
            "Điều kiện hưởng chế độ thai sản gồm thời gian đóng "
            "bảo hiểm xã hội tối thiểu."
        ),
        "article_id": "article_001",
        "source_file": None,
        "keywords": ["thai sản", "chế độ thai sản", "điều kiện hưởng"],
    },
    {
        "text": (
            "Mức đóng bảo hiểm xã hội bắt buộc được tính theo "
            "phần trăm lương cơ bản."
        ),
        "article_id": "article_002",
        "source_file": None,
        "keywords": [
            "bảo hiểm xã hội",
            "mức đóng",
            "bắt buộc",
            "phần trăm",
        ],
    },
    {
        "text": (
            "Người lao động có quyền nghỉ phép năm tối thiểu "
            "theo quy định của luật lao động."
        ),
        "article_id": "article_003",
        "source_file": None,
        "keywords": ["nghỉ phép năm", "tối thiểu", "ngày phép"],
    },
    {
        "text": (
            "Hồ sơ xin cấp lại sổ bảo hiểm xã hội gồm đơn đề nghị "
            "và giấy tờ tùy thân."
        ),
        "article_id": "article_004",
        "source_file": None,
        "keywords": [
            "hồ sơ",
            "cấp lại sổ",
            "bảo hiểm xã hội",
            "giấy tờ",
        ],
    },
    {
        "text": (
            "Thời gian thử việc tối đa phụ thuộc vào tính chất "
            "và mức độ công việc."
        ),
        "article_id": "article_005",
        "source_file": None,
        "keywords": ["thử việc", "tối đa", "thời gian thử việc"],
    },
    {
        "text": (
            "Người lao động được nghỉ phép có hưởng lương khi kết hôn "
            "theo chính sách công ty."
        ),
        "article_id": None,
        "source_file": "hr_policy_2024.pdf",
        "keywords": ["kết hôn", "nghỉ khi kết hôn"],
    },
    {
        "text": (
            "Chính sách làm việc từ xa (remote) áp dụng cho "
            "các phòng ban đủ điều kiện."
        ),
        "article_id": None,
        "source_file": "hr_policy_2024.pdf",
        "keywords": [
            "làm việc từ xa",
            "remote",
            "chính sách làm việc",
        ],
    },
    {
        "text": (
            "Quy trình phê duyệt chi phí công tác yêu cầu hóa đơn "
            "và xác nhận của quản lý."
        ),
        "article_id": None,
        "source_file": "finance_guideline.docx",
        "keywords": [
            "chi phí công tác",
            "phê duyệt",
            "quy trình phê duyệt",
        ],
    },
]


def _normalize(text: str) -> str:
    return " ".join(text.lower().strip().split())


def _validate_filters(filters: Any, case_number: int) -> dict[str, str] | None:
    if filters is None:
        return None

    if not isinstance(filters, dict):
        raise ValueError(
            f"Case {case_number}: filters phải là object/dict."
        )

    normalized: dict[str, str] = {}

    for field, value in filters.items():
        if field not in SUPPORTED_FILTER_FIELDS:
            raise ValueError(
                f"Case {case_number}: filter '{field}' không được hỗ trợ. "
                "Chỉ dùng article_id hoặc source_file."
            )

        if not isinstance(value, str) or not value.strip():
            raise ValueError(
                f"Case {case_number}: giá trị filter '{field}' "
                "phải là chuỗi không rỗng."
            )

        normalized[field] = value.strip()

    return normalized or None


def fake_search_similar_chunks(
    query_text: str,
    top_k: int = DEFAULT_TOP_K,
    filters: dict[str, str] | None = None,
) -> list[dict[str, Any]]:
    """
    Mô phỏng retrieval bằng so khớp keyword.

    Output giữ cùng shape với search_similar_chunks thật:
    text, article_id, source_file, page_number, distance.
    """
    if top_k <= 0:
        raise ValueError("top_k phải lớn hơn 0.")

    normalized_query = _normalize(query_text)
    candidates = FAKE_CORPUS

    if filters:
        candidates = [
            chunk
            for chunk in candidates
            if all(
                chunk.get(field) == value
                for field, value in filters.items()
            )
        ]

    scored: list[dict[str, Any]] = []

    for chunk in candidates:
        matched_keywords = sum(
            1
            for keyword in chunk["keywords"]
            if _normalize(keyword) in normalized_query
        )

        if matched_keywords == 0:
            continue

        distance = round(
            max(
                0.0,
                1 - matched_keywords / len(chunk["keywords"]),
            ),
            3,
        )

        if distance > MOCK_DISTANCE_THRESHOLD:
            continue

        scored.append(
            {
                "text": chunk["text"],
                "article_id": chunk["article_id"],
                "source_file": chunk["source_file"],
                "page_number": None,
                "distance": distance,
            }
        )

    scored.sort(key=lambda item: item["distance"])
    return scored[:top_k]


async def fake_semantic_search_logic(
    query_text: str,
    top_k: int = DEFAULT_TOP_K,
    filters: dict[str, str] | None = None,
) -> list[dict[str, Any]]:
    return fake_search_similar_chunks(
        query_text,
        top_k=top_k,
        filters=filters,
    )


# =============================================================================
# INTEGRATION MODE
# =============================================================================

async def integration_precheck() -> str | None:
    """
    Trả None khi integration sẵn sàng.
    Nếu chưa sẵn sàng, trả chuỗi mô tả lý do để bỏ qua.
    """
    try:
        from app.services.services_vector_db import (
            collection as real_collection,
        )
    except Exception as exc:
        return (
            "Không import được app.services.services_vector_db: "
            f"{exc}"
        )

    try:
        if real_collection.count() == 0:
            return (
                "ChromaDB collection 'chunks' đang rỗng; "
                "chưa có dữ liệu thật được ingest."
            )
    except Exception as exc:
        return f"Không kiểm tra được ChromaDB: {exc}"

    try:
        from app.core.ollama_client import chat as ollama_health_check

        await ollama_health_check()
    except Exception as exc:
        return f"Không kết nối được Ollama: {exc}"

    return None


# =============================================================================
# DATASET
# =============================================================================

def load_dataset(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(
            f"Không tìm thấy fixture: {path}"
        )

    try:
        with path.open("r", encoding="utf-8") as file:
            raw = json.load(file)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"Fixture không phải JSON hợp lệ: {exc}"
        ) from exc

    if isinstance(raw, dict):
        data = raw.get("cases")
    elif isinstance(raw, list):
        data = raw
    else:
        data = None

    if not isinstance(data, list) or not data:
        raise ValueError(
            "Fixture phải là list case hoặc object có key 'cases'."
        )

    if len(data) < 10:
        raise ValueError(
            "Fixture phải có tối thiểu 10 retrieval cases."
        )

    normalized_cases: list[dict[str, Any]] = []
    no_context_count = 0

    for index, case in enumerate(data, start=1):
        if not isinstance(case, dict):
            raise ValueError(
                f"Case {index}: phải là object/dict."
            )

        question = case.get("question")
        if not isinstance(question, str) or not question.strip():
            raise ValueError(
                f"Case {index}: question phải là chuỗi không rỗng."
            )

        expect_no_context = case.get(
            "expect_no_context",
            False,
        )
        if not isinstance(expect_no_context, bool):
            raise ValueError(
                f"Case {index}: expect_no_context phải là boolean."
            )

        expected_source = case.get("expected_source")

        if expect_no_context:
            no_context_count += 1
            if expected_source is not None:
                raise ValueError(
                    f"Case {index}: câu hỏi no-context phải có "
                    "expected_source = null."
                )
        else:
            if (
                not isinstance(expected_source, str)
                or not expected_source.strip()
            ):
                raise ValueError(
                    f"Case {index}: câu hỏi có context phải có "
                    "expected_source là chuỗi không rỗng."
                )
            expected_source = expected_source.strip()

        normalized_cases.append(
            {
                "question": question.strip(),
                "expected_source": expected_source,
                "expect_no_context": expect_no_context,
                "filters": _validate_filters(
                    case.get("filters"),
                    index,
                ),
            }
        )

    if no_context_count < 2:
        raise ValueError(
            "Fixture phải có ít nhất 2 case "
            "expect_no_context=true."
        )

    return normalized_cases


def extract_retrieved_sources(
    chunks: list[dict[str, Any]],
) -> list[str]:
    """
    Lấy cả article_id và source_file.

    Không dùng:
        article_id or source_file

    vì chunk thật có thể chứa đồng thời cả hai metadata.
    """
    sources: list[str] = []

    for chunk in chunks:
        article_id = chunk.get("article_id")
        source_file = chunk.get("source_file")

        if isinstance(article_id, str) and article_id:
            sources.append(article_id)

        if isinstance(source_file, str) and source_file:
            sources.append(source_file)

    # Loại trùng nhưng giữ nguyên thứ tự.
    return list(dict.fromkeys(sources))


def evaluate_case(
    expected_source: str | None,
    expect_no_context: bool,
    retrieved_sources: list[str],
) -> bool:
    if expect_no_context:
        return not retrieved_sources

    return (
        expected_source is not None
        and expected_source in retrieved_sources
    )


def format_sources(sources: list[str]) -> str:
    return ", ".join(sources) if sources else "(rỗng)"


def _shorten(text: str, max_length: int) -> str:
    if len(text) <= max_length:
        return text
    return text[: max_length - 3] + "..."


def print_table(rows: list[dict[str, Any]]) -> None:
    headers = [
        "Question",
        "Expected source",
        "Retrieved sources",
        "Pass/Fail",
    ]

    table_rows: list[list[str]] = []

    for row in rows:
        if row["error"]:
            status = "ERROR"
        else:
            status = "PASS" if row["passed"] else "FAIL"

        table_rows.append(
            [
                _shorten(row["question"], 70),
                row["expected_source"] or "(no context)",
                _shorten(
                    format_sources(row["retrieved_sources"]),
                    60,
                ),
                status,
            ]
        )

    col_widths = [
        max(
            len(headers[column]),
            max(
                (
                    len(row[column])
                    for row in table_rows
                ),
                default=0,
            ),
        )
        for column in range(len(headers))
    ]

    def format_row(columns: list[str]) -> str:
        return " | ".join(
            value.ljust(col_widths[index])
            for index, value in enumerate(columns)
        )

    separator = "-+-".join(
        "-" * width for width in col_widths
    )

    print(format_row(headers))
    print(separator)

    for row in table_rows:
        print(format_row(row))

    error_rows = [row for row in rows if row["error"]]
    if error_rows:
        print("\nChi tiết lỗi:")
        for row in error_rows:
            print(f"- {row['question']}: {row['error']}")


SearchFunction = Callable[
    [str, int, dict[str, str] | None],
    Awaitable[list[dict[str, Any]]],
]


async def run_evaluation(
    dataset: list[dict[str, Any]],
    top_k: int,
    integration_mode: bool,
) -> list[dict[str, Any]]:
    if integration_mode:
        from app.services.services_vector_db import (
            semantic_search_logic,
        )

        search_fn: SearchFunction = semantic_search_logic
    else:
        search_fn = fake_semantic_search_logic

    results: list[dict[str, Any]] = []

    for case in dataset:
        question = case["question"]
        expected_source = case["expected_source"]
        expect_no_context = case["expect_no_context"]
        filters = case["filters"]

        try:
            chunks = await search_fn(
                question,
                top_k=top_k,
                filters=filters,
            )
            retrieved_sources = extract_retrieved_sources(
                chunks
            )
            error = None
            passed = evaluate_case(
                expected_source,
                expect_no_context,
                retrieved_sources,
            )
        except Exception as exc:
            # Lỗi kỹ thuật phải là FAIL.
            # Không được biến thành chunks=[] vì case no-context
            # có thể bị tính PASS giả.
            retrieved_sources = []
            error = f"{type(exc).__name__}: {exc}"
            passed = False

        results.append(
            {
                "question": question,
                "expected_source": expected_source,
                "expect_no_context": expect_no_context,
                "retrieved_sources": retrieved_sources,
                "passed": passed,
                "error": error,
            }
        )

    return results


def print_summary(
    results: list[dict[str, Any]],
    top_k: int,
    integration_mode: bool,
) -> bool:
    total = len(results)
    passed_count = sum(
        1 for result in results if result["passed"]
    )
    error_count = sum(
        1 for result in results if result["error"]
    )

    context_cases = [
        result
        for result in results
        if not result["expect_no_context"]
    ]
    no_context_cases = [
        result
        for result in results
        if result["expect_no_context"]
    ]

    recall_pass = sum(
        1 for result in context_cases if result["passed"]
    )
    no_context_pass = sum(
        1 for result in no_context_cases if result["passed"]
    )

    mode_name = (
        "INTEGRATION (dữ liệu thật)"
        if integration_mode
        else "DEFAULT (fake collection / synthetic)"
    )
    if integration_mode:
        from app.services.services_vector_db import RAG_DISTANCE_THRESHOLD

        threshold_name = str(RAG_DISTANCE_THRESHOLD)
    else:
        threshold_name = str(MOCK_DISTANCE_THRESHOLD)

    print("\n=== SUMMARY ===")
    print(f"Chế độ: {mode_name}")
    print(
        f"top_k = {top_k}, "
        f"distance_threshold = {threshold_name}"
    )
    print(f"Tổng số case: {total}")
    print(
        f"Pass: {passed_count}/{total} "
        f"({passed_count / total:.1%})"
    )
    print(
        f"Recall@{top_k}: "
        f"{recall_pass}/{len(context_cases)} "
        f"({recall_pass / len(context_cases):.1%})"
    )
    print(
        "Tỷ lệ nhận diện đúng câu hỏi không có context: "
        f"{no_context_pass}/{len(no_context_cases)} "
        f"({no_context_pass / len(no_context_cases):.1%})"
    )
    print(f"Lỗi kỹ thuật: {error_count}")

    print("\nDòng có thể sao chép vào PR:")
    print(
        f"Recall@{top_k}: {recall_pass}/{len(context_cases)}; "
        f"no-context: {no_context_pass}/{len(no_context_cases)}; "
        f"pass: {passed_count}/{total}; "
        f"top_k={top_k}; threshold={threshold_name}"
    )

    return passed_count == total


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Đánh giá chất lượng retrieval RAG."
    )
    parser.add_argument(
        "--dataset",
        type=Path,
        default=DEFAULT_DATASET_PATH,
        help=(
            "Đường dẫn tới fixture JSON "
            "(mặc định: tests/fixtures/retrieval_cases.json)"
        ),
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=DEFAULT_TOP_K,
        help=f"Số kết quả retrieval, mặc định {DEFAULT_TOP_K}.",
    )

    args = parser.parse_args()

    if args.top_k <= 0:
        parser.error("--top-k phải lớn hơn 0.")

    return args


def main() -> int:
    args = parse_args()
    integration_mode = (
        os.getenv("RUN_RAG_INTEGRATION") == "1"
    )

    try:
        dataset = load_dataset(args.dataset)
    except (FileNotFoundError, ValueError) as exc:
        print(f"Lỗi dataset: {exc}", file=sys.stderr)
        return 1

    if integration_mode:
        print(
            "=== INTEGRATION: dùng Ollama + ChromaDB thật ==="
        )

        async def run_checked_integration() -> tuple[
            str | None,
            list[dict[str, Any]] | None,
        ]:
            problem = await integration_precheck()
            if problem:
                return problem, None

            results = await run_evaluation(
                dataset,
                top_k=args.top_k,
                integration_mode=True,
            )
            return None, results

        problem, results = asyncio.run(run_checked_integration())
        if problem:
            print(f"Bỏ qua integration test: {problem}")
            return 0
        assert results is not None
    else:
        print(
            "=== DEFAULT: dùng fake collection / "
            "dữ liệu synthetic ==="
        )
        results = asyncio.run(
            run_evaluation(
                dataset,
                top_k=args.top_k,
                integration_mode=False,
            )
        )

    print_table(results)
    all_passed = print_summary(
        results,
        top_k=args.top_k,
        integration_mode=integration_mode,
    )

    return 0 if all_passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
